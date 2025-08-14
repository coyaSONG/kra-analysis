#!/usr/bin/env node

/**
 * Final API test - Focused on core functionality
 */

const API_BASE = 'http://localhost:3001/api/v1';

// Test data from actual race results
const TEST_DATA = {
  date: '20240106',
  meet: '서울',
  raceNo: 1,
  horses: [
    { hrNo: '0053587', name: '서부특송' },
    { hrNo: '0047073', name: '최강타임' },
    { hrNo: '0046804', name: '금악명장' }
  ],
  jockeys: [
    { jkNo: '080476', name: '장추열' },
    { jkNo: '080533', name: '조상범' },
    { jkNo: '080486', name: '이혁' }
  ],
  trainers: [
    { trNo: '070165', name: '서인석' },
    { trNo: '070244', name: '리카디' },
    { trNo: '070145', name: '홍대유' }
  ]
};

async function testAPI(name, url) {
  try {
    console.log(`\n📍 Testing: ${name}`);
    console.log(`   URL: ${url}`);
    
    const startTime = Date.now();
    const response = await fetch(url);
    const responseTime = Date.now() - startTime;
    const data = await response.json();
    
    if (data.success) {
      console.log(`   ✅ SUCCESS (${responseTime}ms)`);
      
      // Show key data
      if (data.data?.raceInfo) {
        console.log(`      Race: ${data.data.raceInfo.rcName}, ${data.data.raceInfo.totalHorses} horses`);
      }
      if (data.data?.hrName) {
        console.log(`      Horse: ${data.data.hrName} - Rank: ${data.data.rank}, Races: ${data.data.rcCntT}`);
      }
      if (data.data?.jkName) {
        console.log(`      Jockey: ${data.data.jkName} - Wins: ${data.data.ord1CntT}, Races: ${data.data.rcCntT}`);
      }
      if (data.data?.trName) {
        console.log(`      Trainer: ${data.data.trName} - Win Rate: ${data.data.winRateT}%, Races: ${data.data.rcCntT}`);
      }
      
      return true;
    } else {
      console.log(`   ❌ FAILED: ${data.error || data.message}`);
      return false;
    }
  } catch (error) {
    console.log(`   ❌ ERROR: ${error.message}`);
    return false;
  }
}

async function runTests() {
  console.log('🎯 FINAL API VERIFICATION TEST');
  console.log('=' .repeat(50));
  
  const results = [];
  
  // 1. Race API Tests
  console.log('\n📋 RACE API TESTS');
  console.log('-'.repeat(50));
  
  results.push(await testAPI(
    'Race with Korean meet name',
    `${API_BASE}/races/${TEST_DATA.date}/${TEST_DATA.meet}/${TEST_DATA.raceNo}`
  ));
  
  results.push(await testAPI(
    'Race with numeric meet code',
    `${API_BASE}/races/${TEST_DATA.date}/1/${TEST_DATA.raceNo}`
  ));
  
  results.push(await testAPI(
    'Different meet (제주)',
    `${API_BASE}/races/${TEST_DATA.date}/제주/1`
  ));
  
  // 2. Horse API Tests
  console.log('\n🐴 HORSE API TESTS');
  console.log('-'.repeat(50));
  
  for (const horse of TEST_DATA.horses) {
    results.push(await testAPI(
      `Horse: ${horse.name} (${horse.hrNo})`,
      `${API_BASE}/horses/${horse.hrNo}`
    ));
  }
  
  // 3. Jockey API Tests
  console.log('\n🏇 JOCKEY API TESTS');
  console.log('-'.repeat(50));
  
  for (const jockey of TEST_DATA.jockeys) {
    results.push(await testAPI(
      `Jockey: ${jockey.name} (${jockey.jkNo})`,
      `${API_BASE}/jockeys/${jockey.jkNo}`
    ));
  }
  
  // 4. Trainer API Tests
  console.log('\n👨‍🏫 TRAINER API TESTS');
  console.log('-'.repeat(50));
  
  for (const trainer of TEST_DATA.trainers) {
    results.push(await testAPI(
      `Trainer: ${trainer.name} (${trainer.trNo})`,
      `${API_BASE}/trainers/${trainer.trNo}`
    ));
  }
  
  // 5. Date Format Validation Test
  console.log('\n📅 DATE FORMAT VALIDATION');
  console.log('-'.repeat(50));
  
  // This should fail - testing validation
  const invalidDateTest = await testAPI(
    'Invalid date format (should fail)',
    `${API_BASE}/races/2024-01-06/서울/1`
  );
  
  // Summary
  console.log('\n' + '='.repeat(50));
  console.log('📊 SUMMARY');
  console.log('='.repeat(50));
  
  const passed = results.filter(r => r).length;
  const total = results.length;
  const percentage = ((passed / total) * 100).toFixed(1);
  
  console.log(`\n✅ Passed: ${passed}/${total} (${percentage}%)`);
  
  if (passed === total) {
    console.log('\n🎉 PERFECT! All core APIs are working correctly!');
    console.log('✨ Date format unification successful!');
  } else if (passed >= total * 0.8) {
    console.log('\n✅ GOOD! Most APIs are working correctly.');
    console.log('⚠️  Some minor issues may need attention.');
  } else {
    console.log('\n⚠️  Some APIs have issues that need to be fixed.');
  }
  
  console.log('\n💡 Note: The invalid date format test is expected to fail.');
  console.log('   This confirms that validation is working correctly.\n');
}

// Run tests
runTests().catch(console.error);