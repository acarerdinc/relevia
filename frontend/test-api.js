// Simple Node.js script to test the API from frontend perspective
const https = require('https');
const http = require('http');

const BASE_URL = 'http://localhost:8000/api/v1';

async function testAPI() {
    console.log('🧪 Testing API from frontend perspective...');
    
    try {
        // Test CORS preflight
        console.log('\n1. Testing CORS...');
        const corsResponse = await fetch(`${BASE_URL}/health`, {
            method: 'GET',
            headers: {
                'Origin': 'http://localhost:3000',
                'Content-Type': 'application/json'
            }
        });
        console.log(`CORS Status: ${corsResponse.status}`);
        
        // Test topics
        console.log('\n2. Testing topics...');
        const topicsResponse = await fetch(`${BASE_URL}/topics/flat`);
        const topicsData = await topicsResponse.json();
        console.log(`Topics: ${topicsData.topics.length} found`);
        
        // Test quiz start
        const testTopic = topicsData.topics.find(t => t.parent_id !== null);
        if (testTopic) {
            console.log(`\n3. Testing quiz start with topic: ${testTopic.name}`);
            const quizResponse = await fetch(`${BASE_URL}/quiz/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Origin': 'http://localhost:3000'
                },
                body: JSON.stringify({
                    topic_id: testTopic.id,
                    user_id: 1
                })
            });
            
            if (quizResponse.ok) {
                const quizData = await quizResponse.json();
                console.log(`Quiz started: Session ${quizData.session_id}`);
                
                // Test getting question
                console.log('\n4. Testing question generation...');
                const questionResponse = await fetch(`${BASE_URL}/quiz/question/${quizData.session_id}`);
                if (questionResponse.ok) {
                    const questionData = await questionResponse.json();
                    console.log(`Question: ${questionData.question}`);
                    console.log(`Options: ${questionData.options.length} choices`);
                    console.log('✅ All API tests passed!');
                } else {
                    console.log(`❌ Question failed: ${questionResponse.status}`);
                    console.log(await questionResponse.text());
                }
            } else {
                console.log(`❌ Quiz start failed: ${quizResponse.status}`);
                console.log(await quizResponse.text());
            }
        }
        
    } catch (error) {
        console.error('❌ Test failed:', error.message);
    }
}

// Check if fetch is available (Node 18+)
if (typeof fetch === 'undefined') {
    console.log('❌ This test requires Node.js 18+ for fetch API');
    process.exit(1);
}

testAPI();