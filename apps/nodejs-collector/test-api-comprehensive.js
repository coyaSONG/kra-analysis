#!/usr/bin/env node

/**
 * Comprehensive API test after date format unification
 * Tests all endpoints with various scenarios
 */

const API_BASE = 'http://localhost:3001/api/v1';

// Test configuration
const TEST_CONFIG = {
  date: '20240106',
  meet: '서울',
  raceNo: 1,
  horseNo: '0053587',  // 서부특송
  jockeyNo: '080476',  // 장추열
  trainerNo: '070165', // 서인석
};

// Color codes for output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

async function testEndpoint(category, name, url, method = 'GET', body = null) {
  const startTime = Date.now();
  console.log(`\n${colors.cyan}[${category}]${colors.reset} ${name}`);
  console.log(`  📍 ${method} ${url}`);
  
  try {
    const options = {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
    };
    
    if (body) {
      options.body = JSON.stringify(body);
    }
    
    const response = await fetch(url, options);
    const responseTime = Date.now() - startTime;
    const data = await response.json();
    
    if (data.success) {
      console.log(`  ${colors.green}✅ SUCCESS${colors.reset} (${responseTime}ms)`);
      
      // Display key information based on endpoint type
      if (data.data) {
        if (data.data.raceInfo) {
          console.log(`     • Race: ${data.data.raceInfo.rcName}`);
          console.log(`     • Horses: ${data.data.raceInfo.totalHorses}`);
          console.log(`     • Date: ${data.data.raceInfo.date}`);
        }
        if (data.data.hrName) {
          console.log(`     • Horse: ${data.data.hrName} (${data.data.rank || 'N/A'})`);
          console.log(`     • Owner: ${data.data.owName}`);
          console.log(`     • Total Races: ${data.data.rcCntT || 0}`);
        }
        if (data.data.jkName) {
          console.log(`     • Jockey: ${data.data.jkName}`);
          console.log(`     • Win Rate: ${data.data.ord1CntT}/${data.data.rcCntT}`);
          console.log(`     • Age: ${data.data.age}`);
        }
        if (data.data.trName) {
          console.log(`     • Trainer: ${data.data.trName}`);
          console.log(`     • Win Rate: ${data.data.winRateT}%`);
          console.log(`     • Total Races: ${data.data.rcCntT}`);
        }
      }
      
      return { success: true, responseTime };
    } else {
      console.log(`  ${colors.red}❌ FAILED${colors.reset}: ${data.error || data.message}`);
      if (data.details) {
        console.log(`     Details:`, JSON.stringify(data.details, null, 2));
      }
      return { success: false, responseTime, error: data.error };
    }
  } catch (error) {
    const responseTime = Date.now() - startTime;
    console.log(`  ${colors.red}❌ ERROR${colors.reset}: ${error.message}`);
    return { success: false, responseTime, error: error.message };
  }
}

async function runAllTests() {
  console.log(`${colors.blue}${'═'.repeat(60)}${colors.reset}`);
  console.log(`${colors.blue}🚀 COMPREHENSIVE API TEST SUITE${colors.reset}`);
  console.log(`${colors.blue}${'═'.repeat(60)}${colors.reset}`);
  console.log(`📅 Test Date: ${TEST_CONFIG.date}`);
  console.log(`🏟️  Test Meet: ${TEST_CONFIG.meet}`);
  console.log(`🏇 Test Race: ${TEST_CONFIG.raceNo}`);
  
  const results = [];
  const startTime = Date.now();
  
  // =================================================================
  // RACE API TESTS
  // =================================================================
  console.log(`\n${colors.yellow}${'─'.repeat(60)}${colors.reset}`);
  console.log(`${colors.yellow}📋 RACE API TESTS${colors.reset}`);
  console.log(`${colors.yellow}${'─'.repeat(60)}${colors.reset}`);
  
  // Test 1: Get specific race
  results.push(await testEndpoint(
    'RACE',
    'Get Specific Race Details',
    `${API_BASE}/races/${TEST_CONFIG.date}/${TEST_CONFIG.meet}/${TEST_CONFIG.raceNo}`
  ));
  
  // Test 2: Get race with enriched data
  results.push(await testEndpoint(
    'RACE',
    'Get Race with Enriched Data',
    `${API_BASE}/races/${TEST_CONFIG.date}/${TEST_CONFIG.meet}/${TEST_CONFIG.raceNo}?includeEnriched=true`
  ));
  
  // Test 3: Try different meet (제주)
  results.push(await testEndpoint(
    'RACE',
    'Get Race - Different Meet (제주)',
    `${API_BASE}/races/${TEST_CONFIG.date}/제주/1`
  ));
  
  // Test 4: Try numeric meet code
  results.push(await testEndpoint(
    'RACE',
    'Get Race - Numeric Meet Code',
    `${API_BASE}/races/${TEST_CONFIG.date}/1/1`
  ));
  
  // =================================================================
  // HORSE API TESTS
  // =================================================================
  console.log(`\n${colors.yellow}${'─'.repeat(60)}${colors.reset}`);
  console.log(`${colors.yellow}🐴 HORSE API TESTS${colors.reset}`);
  console.log(`${colors.yellow}${'─'.repeat(60)}${colors.reset}`);
  
  // Test 5: Get horse details
  results.push(await testEndpoint(
    'HORSE',
    'Get Horse Details',
    `${API_BASE}/horses/${TEST_CONFIG.horseNo}`
  ));
  
  // Test 6: Get horse history
  results.push(await testEndpoint(
    'HORSE',
    'Get Horse Race History',
    `${API_BASE}/horses/${TEST_CONFIG.horseNo}/history`
  ));
  
  // Test 7: Search horses
  results.push(await testEndpoint(
    'HORSE',
    'Search Horses',
    `${API_BASE}/horses?hrName=서부&meet=${TEST_CONFIG.meet}`
  ));
  
  // Test 8: Different horse
  results.push(await testEndpoint(
    'HORSE',
    'Get Different Horse (최강타임)',
    `${API_BASE}/horses/0047073`
  ));
  
  // =================================================================
  // JOCKEY API TESTS
  // =================================================================
  console.log(`\n${colors.yellow}${'─'.repeat(60)}${colors.reset}`);
  console.log(`${colors.yellow}🏇 JOCKEY API TESTS${colors.reset}`);
  console.log(`${colors.yellow}${'─'.repeat(60)}${colors.reset}`);
  
  // Test 9: Get jockey details
  results.push(await testEndpoint(
    'JOCKEY',
    'Get Jockey Details',
    `${API_BASE}/jockeys/${TEST_CONFIG.jockeyNo}`
  ));
  
  // Test 10: Get jockey stats
  results.push(await testEndpoint(
    'JOCKEY',
    'Get Jockey Statistics',
    `${API_BASE}/jockeys/${TEST_CONFIG.jockeyNo}/stats`
  ));
  
  // Test 11: Different jockey
  results.push(await testEndpoint(
    'JOCKEY',
    'Get Different Jockey (조상범)',
    `${API_BASE}/jockeys/080533`
  ));
  
  // =================================================================
  // TRAINER API TESTS
  // =================================================================
  console.log(`\n${colors.yellow}${'─'.repeat(60)}${colors.reset}`);
  console.log(`${colors.yellow}👨‍🏫 TRAINER API TESTS${colors.reset}`);
  console.log(`${colors.yellow}${'─'.repeat(60)}${colors.reset}`);
  
  // Test 12: Get trainer details
  results.push(await testEndpoint(
    'TRAINER',
    'Get Trainer Details',
    `${API_BASE}/trainers/${TEST_CONFIG.trainerNo}`
  ));
  
  // Test 13: Get trainer stats
  results.push(await testEndpoint(
    'TRAINER',
    'Get Trainer Statistics',
    `${API_BASE}/trainers/${TEST_CONFIG.trainerNo}/stats`
  ));
  
  // Test 14: Different trainer
  results.push(await testEndpoint(
    'TRAINER',
    'Get Different Trainer (리카디)',
    `${API_BASE}/trainers/070244`
  ));
  
  // =================================================================
  // ERROR HANDLING TESTS
  // =================================================================
  console.log(`\n${colors.yellow}${'─'.repeat(60)}${colors.reset}`);
  console.log(`${colors.yellow}⚠️  ERROR HANDLING TESTS${colors.reset}`);
  console.log(`${colors.yellow}${'─'.repeat(60)}${colors.reset}`);
  
  // Test 15: Invalid date format
  results.push(await testEndpoint(
    'ERROR',
    'Invalid Date Format (should fail)',
    `${API_BASE}/races/2024-01-06/서울/1`
  ));
  
  // Test 16: Non-existent horse
  results.push(await testEndpoint(
    'ERROR',
    'Non-existent Horse',
    `${API_BASE}/horses/9999999`
  ));
  
  // Test 17: Invalid race number
  results.push(await testEndpoint(
    'ERROR',
    'Invalid Race Number',
    `${API_BASE}/races/${TEST_CONFIG.date}/${TEST_CONFIG.meet}/99`
  ));
  
  // =================================================================
  // SUMMARY
  // =================================================================
  const totalTime = Date.now() - startTime;
  const passed = results.filter(r => r.success).length;
  const failed = results.filter(r => !r.success).length;
  const avgResponseTime = Math.round(
    results.reduce((sum, r) => sum + r.responseTime, 0) / results.length
  );
  
  console.log(`\n${colors.blue}${'═'.repeat(60)}${colors.reset}`);
  console.log(`${colors.blue}📊 TEST SUMMARY${colors.reset}`);
  console.log(`${colors.blue}${'═'.repeat(60)}${colors.reset}`);
  
  console.log(`\n📈 Results:`);
  console.log(`   ${colors.green}✅ Passed: ${passed}${colors.reset}`);
  console.log(`   ${colors.red}❌ Failed: ${failed}${colors.reset}`);
  console.log(`   📊 Success Rate: ${((passed / results.length) * 100).toFixed(1)}%`);
  
  console.log(`\n⏱️  Performance:`);
  console.log(`   • Total Time: ${totalTime}ms`);
  console.log(`   • Average Response: ${avgResponseTime}ms`);
  console.log(`   • Fastest: ${Math.min(...results.map(r => r.responseTime))}ms`);
  console.log(`   • Slowest: ${Math.max(...results.map(r => r.responseTime))}ms`);
  
  // Expected failures (error handling tests)
  const expectedFailures = 3; // Tests 15, 16, 17 should fail
  const actualExpectedFailures = results.slice(-3).filter(r => !r.success).length;
  
  console.log(`\n🎯 Error Handling:`);
  console.log(`   • Expected Failures: ${expectedFailures}`);
  console.log(`   • Actual Failures in Error Tests: ${actualExpectedFailures}`);
  
  if (actualExpectedFailures === expectedFailures && passed >= results.length - expectedFailures) {
    console.log(`\n${colors.green}🎉 ALL TESTS PASSED! The API is working correctly.${colors.reset}`);
    console.log(`${colors.green}✨ Date format unification successful!${colors.reset}`);
  } else {
    console.log(`\n${colors.red}⚠️  Some unexpected failures detected.${colors.reset}`);
    console.log(`${colors.red}Please review the failed tests above.${colors.reset}`);
  }
  
  console.log(`\n${colors.blue}${'═'.repeat(60)}${colors.reset}\n`);
}

// Run the tests
runAllTests().catch(console.error);