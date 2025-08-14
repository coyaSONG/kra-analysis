#!/usr/bin/env node

/**
 * API Regression Test Suite
 * 
 * Runs before and after code changes to ensure no breaking changes
 * Usage: node test-regression.js [--baseline|--compare]
 */

const fs = require('fs').promises;
const path = require('path');

const API_BASE = 'http://localhost:3001/api/v1';
const BASELINE_FILE = 'test-baseline.json';

// Critical endpoints that must always work
const CRITICAL_ENDPOINTS = [
  {
    name: 'Race API - Get Race',
    method: 'GET',
    url: '/races/20240106/서울/1',
    expectedFields: ['raceInfo', 'raceResult']
  },
  {
    name: 'Horse API - Get Details',
    method: 'GET',
    url: '/horses/0053587',
    expectedFields: ['hrName', 'rank', 'owName']
  },
  {
    name: 'Jockey API - Get Details',
    method: 'GET',
    url: '/jockeys/080476',
    expectedFields: ['jkName', 'age', 'rcCntT']
  },
  {
    name: 'Trainer API - Get Details',
    method: 'GET',
    url: '/trainers/070165',
    expectedFields: ['trName', 'winRateT', 'rcCntT']
  }
];

async function testEndpoint(endpoint) {
  try {
    const response = await fetch(`${API_BASE}${endpoint.url}`, {
      method: endpoint.method,
      headers: { 'Content-Type': 'application/json' }
    });
    
    const data = await response.json();
    
    return {
      name: endpoint.name,
      url: endpoint.url,
      status: response.status,
      success: data.success,
      hasExpectedFields: endpoint.expectedFields.every(field => 
        data.data && (data.data[field] !== undefined || 
        JSON.stringify(data.data).includes(field))
      ),
      responseTime: response.headers.get('x-response-time'),
      timestamp: new Date().toISOString()
    };
  } catch (error) {
    return {
      name: endpoint.name,
      url: endpoint.url,
      status: 0,
      success: false,
      error: error.message,
      timestamp: new Date().toISOString()
    };
  }
}

async function runTests() {
  console.log('🔍 Running API Regression Tests...\n');
  
  const results = [];
  
  for (const endpoint of CRITICAL_ENDPOINTS) {
    process.stdout.write(`Testing: ${endpoint.name}... `);
    const result = await testEndpoint(endpoint);
    results.push(result);
    
    if (result.success) {
      console.log('✅');
    } else {
      console.log(`❌ (Status: ${result.status})`);
    }
  }
  
  return results;
}

async function saveBaseline(results) {
  await fs.writeFile(
    BASELINE_FILE,
    JSON.stringify(results, null, 2)
  );
  console.log(`\n📝 Baseline saved to ${BASELINE_FILE}`);
}

async function compareWithBaseline(results) {
  try {
    const baselineData = await fs.readFile(BASELINE_FILE, 'utf-8');
    const baseline = JSON.parse(baselineData);
    
    console.log('\n📊 Regression Test Results:\n');
    console.log('='.repeat(60));
    
    let hasRegression = false;
    
    for (let i = 0; i < results.length; i++) {
      const current = results[i];
      const base = baseline[i];
      
      if (!base) {
        console.log(`⚠️  New endpoint: ${current.name}`);
        continue;
      }
      
      console.log(`\n${current.name}:`);
      console.log(`  Status: ${base.status} → ${current.status}`);
      console.log(`  Success: ${base.success} → ${current.success}`);
      
      if (base.success && !current.success) {
        console.log(`  ❌ REGRESSION DETECTED!`);
        hasRegression = true;
      } else if (!base.success && current.success) {
        console.log(`  ✨ IMPROVEMENT!`);
      } else if (base.success && current.success) {
        console.log(`  ✅ No regression`);
      }
      
      if (current.hasExpectedFields === false) {
        console.log(`  ⚠️  Missing expected fields`);
      }
    }
    
    console.log('\n' + '='.repeat(60));
    
    if (hasRegression) {
      console.log('\n❌ REGRESSION DETECTED! Some APIs that were working are now broken.');
      process.exit(1);
    } else {
      console.log('\n✅ No regressions detected. All critical APIs are stable.');
    }
    
  } catch (error) {
    console.log('\n⚠️  No baseline found. Run with --baseline first.');
  }
}

async function main() {
  const args = process.argv.slice(2);
  const mode = args[0];
  
  console.log('🚀 API Regression Test Suite\n');
  
  // Check if server is running
  try {
    const health = await fetch(`${API_BASE.replace('/api/v1', '/health')}`);
    if (!health.ok) throw new Error('Server not healthy');
  } catch (error) {
    console.error('❌ Server is not running on port 3001');
    console.log('💡 Start the server with: npm start');
    process.exit(1);
  }
  
  const results = await runTests();
  
  if (mode === '--baseline') {
    await saveBaseline(results);
    console.log('\n✅ Baseline created successfully!');
    console.log('💡 Run without --baseline to compare future changes.');
  } else if (mode === '--compare' || !mode) {
    await compareWithBaseline(results);
  } else {
    console.log('\nUsage:');
    console.log('  node test-regression.js --baseline  # Create baseline');
    console.log('  node test-regression.js --compare   # Compare with baseline');
    console.log('  node test-regression.js             # Compare with baseline (default)');
  }
}

main().catch(console.error);