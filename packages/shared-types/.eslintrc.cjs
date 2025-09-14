module.exports = {
  root: true,
  extends: [require.resolve('@repo/eslint-config/node.js')],
  parserOptions: {
    tsconfigRootDir: __dirname,
    project: ['./tsconfig.json'],
  },
  ignorePatterns: ['dist/**'],
};

