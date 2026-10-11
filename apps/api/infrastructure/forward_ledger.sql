-- Installed explicitly into a dedicated research schema by its owner.
CREATE SCHEMA __SCHEMA__;
REVOKE ALL ON SCHEMA __SCHEMA__ FROM PUBLIC;

CREATE TABLE __SCHEMA__.studies (
    study_id text PRIMARY KEY,
    race_date text NOT NULL,
    synthetic boolean NOT NULL,
    payload text NOT NULL,
    sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    earliest_cutoff timestamptz NOT NULL,
    registered_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    writer_xid xid8 NOT NULL DEFAULT pg_current_xact_id(),
    UNIQUE (race_date, synthetic)
);
CREATE TABLE __SCHEMA__.members (
    study_id text NOT NULL REFERENCES __SCHEMA__.studies,
    race_id text NOT NULL,
    cutoff_at timestamptz NOT NULL,
    PRIMARY KEY (study_id, race_id)
);
CREATE TABLE __SCHEMA__.study_observations (
    study_id text PRIMARY KEY REFERENCES __SCHEMA__.studies,
    observed_committed_at timestamptz NOT NULL,
    timely boolean NOT NULL
);
CREATE TABLE __SCHEMA__.submissions (
    study_id text NOT NULL,
    race_id text NOT NULL,
    arm_id text NOT NULL CHECK (arm_id = 'b0_numeric_gate_v1'),
    payload text NOT NULL,
    sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    registered_at timestamptz NOT NULL,
    writer_xid xid8 NOT NULL,
    PRIMARY KEY (study_id, race_id, arm_id),
    FOREIGN KEY (study_id, race_id) REFERENCES __SCHEMA__.members
);
CREATE TABLE __SCHEMA__.observations (
    study_id text NOT NULL,
    race_id text NOT NULL,
    arm_id text NOT NULL,
    observed_committed_at timestamptz NOT NULL,
    timely boolean NOT NULL,
    PRIMARY KEY (study_id, race_id, arm_id),
    FOREIGN KEY (study_id, race_id, arm_id) REFERENCES __SCHEMA__.submissions
);

CREATE FUNCTION __SCHEMA__.immutable_row() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    RAISE EXCEPTION 'forward_ledger_is_append_only';
END $$;
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON __SCHEMA__.studies
FOR EACH ROW EXECUTE FUNCTION __SCHEMA__.immutable_row();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON __SCHEMA__.members
FOR EACH ROW EXECUTE FUNCTION __SCHEMA__.immutable_row();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON __SCHEMA__.study_observations
FOR EACH ROW EXECUTE FUNCTION __SCHEMA__.immutable_row();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON __SCHEMA__.submissions
FOR EACH ROW EXECUTE FUNCTION __SCHEMA__.immutable_row();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON __SCHEMA__.observations
FOR EACH ROW EXECUTE FUNCTION __SCHEMA__.immutable_row();

CREATE FUNCTION __SCHEMA__.observe_study(p_study text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE s __SCHEMA__.studies; t timestamptz; result jsonb;
BEGIN
    SELECT * INTO STRICT s FROM __SCHEMA__.studies WHERE study_id = p_study;
    IF s.writer_xid = pg_current_xact_id() THEN
        RAISE EXCEPTION 'cannot_witness_own_transaction';
    END IF;
    t := clock_timestamp();
    INSERT INTO __SCHEMA__.study_observations VALUES (p_study, t, t < s.earliest_cutoff)
    ON CONFLICT DO NOTHING;
    SELECT to_jsonb(o) INTO result FROM __SCHEMA__.study_observations o WHERE study_id = p_study;
    RETURN result;
END $$;

CREATE FUNCTION __SCHEMA__.submit(p_study text, p_race text, p_payload text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE
    m __SCHEMA__.members; existing __SCHEMA__.submissions;
    body jsonb; item jsonb; roster jsonb; chosen jsonb; n integer;
    gates integer[] := '{}'; horses text[] := '{}'; t timestamptz;
    universe_hash text; implementation_hash text; result jsonb;
BEGIN
    -- Lock before checking the wall clock; a queued transaction cannot backdate.
    SELECT * INTO STRICT m FROM __SCHEMA__.members
    WHERE study_id = p_study AND race_id = p_race FOR UPDATE;
    SELECT * INTO existing FROM __SCHEMA__.submissions
    WHERE study_id = p_study AND race_id = p_race AND arm_id = 'b0_numeric_gate_v1';
    IF FOUND THEN
        IF existing.payload <> p_payload OR p_payload IS NULL THEN
            RAISE EXCEPTION 'forward_payload_conflict';
        END IF;
        RETURN to_jsonb(existing) - 'writer_xid';
    END IF;
    t := clock_timestamp();
    IF t >= m.cutoff_at THEN RAISE EXCEPTION 'forward_deadline_passed'; END IF;
    IF NOT EXISTS (SELECT 1 FROM __SCHEMA__.study_observations
                   WHERE study_id = p_study AND timely) THEN
        RAISE EXCEPTION 'universe_commit_not_witnessed_before_cutoff';
    END IF;
    SELECT sha256, payload::jsonb->>'b0_implementation_sha256' INTO universe_hash, implementation_hash
    FROM __SCHEMA__.studies WHERE study_id = p_study;
    body := p_payload::jsonb;
    IF (body->>'format_version') IS DISTINCT FROM 'kra-forward-b0-v1'
       OR (body->>'race_id') IS DISTINCT FROM p_race
       OR (body->>'arm_id') IS DISTINCT FROM 'b0_numeric_gate_v1'
       OR (body->>'universe_sha256') IS DISTINCT FROM universe_hash
       OR implementation_hash IS NULL
       OR (body->>'implementation_sha256') IS DISTINCT FROM implementation_hash
       OR jsonb_typeof(body->'roster') IS DISTINCT FROM 'array'
       OR jsonb_typeof(body->'selection') IS DISTINCT FROM 'array'
       OR (body->'source'->>'manifest_sha256') IS NULL
       OR (body->'source'->>'manifest_sha256') !~ '^[0-9a-f]{64}$'
       OR (body->'source'->>'available_at') IS NULL
       OR (body->'source'->>'available_at') !~ '(Z|[+]00:00)$'
       OR (body->'source'->>'available_at')::timestamptz > t
       OR (body->'source'->>'available_at')::timestamptz >= m.cutoff_at THEN
        RAISE EXCEPTION 'invalid_forward_payload';
    END IF;
    roster := body->'roster';
    IF jsonb_array_length(roster) NOT BETWEEN 3 AND 20 THEN
        RAISE EXCEPTION 'invalid_forward_roster';
    END IF;
    FOR item IN SELECT value FROM jsonb_array_elements(roster) LOOP
        IF jsonb_typeof(item->'chul_no') IS DISTINCT FROM 'number'
           OR (item->>'chul_no') !~ '^[0-9]+$'
           OR jsonb_typeof(item->'horse_id') IS DISTINCT FROM 'string'
           OR (item->>'horse_id') !~ '^[1-9][0-9]{0,7}$' THEN
            RAISE EXCEPTION 'invalid_forward_identity';
        END IF;
        n := (item->>'chul_no')::integer;
        IF n NOT BETWEEN 1 AND 20 OR n = ANY(gates) OR (item->>'horse_id') = ANY(horses) THEN
            RAISE EXCEPTION 'duplicate_or_invalid_forward_identity';
        END IF;
        gates := array_append(gates, n);
        horses := array_append(horses, item->>'horse_id');
    END LOOP;
    SELECT jsonb_agg(horse_id ORDER BY gate) INTO chosen FROM (
        SELECT value->>'horse_id' horse_id, (value->>'chul_no')::integer gate
        FROM jsonb_array_elements(roster) ORDER BY gate LIMIT 3
    ) first_three;
    IF chosen IS DISTINCT FROM body->'selection' THEN
        RAISE EXCEPTION 'selection_does_not_match_frozen_b0_rule';
    END IF;
    INSERT INTO __SCHEMA__.submissions VALUES (
        p_study, p_race, 'b0_numeric_gate_v1', p_payload,
        encode(sha256(convert_to(p_payload, 'UTF8')), 'hex'), t, pg_current_xact_id()
    ) RETURNING to_jsonb(submissions) - 'writer_xid' INTO result;
    RETURN result;
END $$;

CREATE FUNCTION __SCHEMA__.observe(p_study text, p_race text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE s __SCHEMA__.submissions; t timestamptz; deadline timestamptz; result jsonb;
BEGIN
    SELECT * INTO STRICT s FROM __SCHEMA__.submissions
    WHERE study_id = p_study AND race_id = p_race AND arm_id = 'b0_numeric_gate_v1';
    IF s.writer_xid = pg_current_xact_id() THEN
        RAISE EXCEPTION 'cannot_witness_own_transaction';
    END IF;
    t := clock_timestamp();
    SELECT cutoff_at INTO STRICT deadline FROM __SCHEMA__.members
    WHERE study_id = p_study AND race_id = p_race;
    INSERT INTO __SCHEMA__.observations VALUES (p_study, p_race, s.arm_id, t, t < deadline)
    ON CONFLICT DO NOTHING;
    SELECT to_jsonb(o) INTO result FROM __SCHEMA__.observations o
    WHERE study_id = p_study AND race_id = p_race AND arm_id = s.arm_id;
    RETURN result;
END $$;

REVOKE ALL ON ALL TABLES IN SCHEMA __SCHEMA__ FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA __SCHEMA__ FROM PUBLIC;
