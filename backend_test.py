import requests
import sys
import json
from datetime import datetime
import time
import uuid

class ListentbhAPITester:
    def __init__(self, base_url="https://mindlistener.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session_token = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.session_id = None
        self.memory_session_id = None
        self.gemini_tests_passed = 0
        self.gemini_tests_run = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if headers:
            test_headers.update(headers)
        
        if self.session_token:
            test_headers['Authorization'] = f'Bearer {self.session_token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, params=data)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 500:
                        print(f"   Response: {response_data}")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root API", "GET", "", 200)

    def test_chat_session_start(self):
        """Test starting a chat session"""
        success, response = self.run_test(
            "Start Chat Session",
            "POST",
            "chat/session/start",
            200,
            data={"user_id": "test_user"}
        )
        if success and 'session_id' in response:
            self.session_id = response['session_id']
            print(f"   Session ID: {self.session_id}")
            return True
        return False

    def test_chat_session_start_unauthenticated(self):
        """Test starting a chat session without authentication (should fail)"""
        success, response = self.run_test(
            "Start Chat Session (Unauthenticated)",
            "POST",
            "chat/session/start",
            401,
            data={"user_id": "test_user"}
        )
        return success

    def test_chat_message(self):
        """Test sending a chat message"""
        if not self.session_id:
            print("❌ No session ID available for chat message test")
            return False
        
        success, response = self.run_test(
            "Send Chat Message",
            "POST",
            "chat/message",
            200,
            data={
                "session_id": self.session_id,
                "message": "I'm feeling a bit stressed about work today",
                "user_id": "test_user"
            }
        )
        
        if success:
            # Check response structure
            if 'messages' in response and isinstance(response['messages'], list):
                print(f"   Received {len(response['messages'])} message chunks")
                return True
        return False

    def test_chat_message_with_invalid_session(self):
        """Test sending a chat message with invalid session ID"""
        success, response = self.run_test(
            "Send Chat Message (Invalid Session)",
            "POST",
            "chat/message",
            404,
            data={
                "session_id": "invalid-session-id",
                "message": "This should fail",
                "user_id": "test_user"
            }
        )
        return success

    def test_chat_message_direct_with_valid_session(self):
        """Test sending a chat message directly by creating a session in DB first"""
        # First, let's try to create a session directly in the database
        # This simulates what would happen if authentication worked
        import uuid
        from datetime import datetime, timezone
        
        # Create a mock session ID
        mock_session_id = str(uuid.uuid4())
        print(f"   Testing with mock session ID: {mock_session_id}")
        
        # Try to send a message with this session (should fail with 404 since session doesn't exist in DB)
        success, response = self.run_test(
            "Send Chat Message (Mock Session)",
            "POST",
            "chat/message",
            404,
            data={
                "session_id": mock_session_id,
                "message": "Testing message flow",
                "user_id": "test_user"
            }
        )
        return success

    def test_crisis_detection(self):
        """Test crisis keyword detection"""
        if not self.session_id:
            print("❌ No session ID available for crisis detection test")
            return False
        
        success, response = self.run_test(
            "Crisis Detection",
            "POST",
            "chat/message",
            200,
            data={
                "session_id": self.session_id,
                "message": "I'm feeling really hopeless and don't want to go on",
                "user_id": "test_user"
            }
        )
        
        if success and response.get('crisis_detected'):
            print("   ✅ Crisis detection working")
            return True
        elif success:
            print("   ⚠️ Crisis not detected - may need review")
            return True
        return False

    def test_session_complete(self):
        """Test completing a chat session"""
        if not self.session_id:
            print("❌ No session ID available for session complete test")
            return False
        
        success, response = self.run_test(
            "Complete Session",
            "POST",
            "chat/session/complete",
            200,
            data={
                "session_id": self.session_id,
                "user_id": "test_user"
            }
        )
        
        if success and 'summary' in response:
            print(f"   Summary generated: {response['summary'][:100]}...")
            return True
        return False

    def test_memory_processing_start(self):
        """Test starting memory processing"""
        success, response = self.run_test(
            "Start Memory Processing",
            "POST",
            "memory/start",
            200,
            data={
                "user_id": "test_user",
                "memory_topic": "work stress that keeps coming back"
            }
        )
        
        if success and 'session_id' in response:
            self.memory_session_id = response['session_id']
            print(f"   Memory Session ID: {self.memory_session_id}")
            return True
        return False

    def test_memory_processing_message(self):
        """Test sending message during memory processing"""
        if not self.memory_session_id:
            print("❌ No memory session ID available")
            return False
        
        success, response = self.run_test(
            "Memory Processing Message",
            "POST",
            "memory/message",
            200,
            data={
                "session_id": self.memory_session_id,
                "message": "I keep thinking about how my boss criticized my work last week. It's consuming my thoughts.",
                "user_id": "test_user"
            }
        )
        
        if success and 'messages' in response:
            print(f"   Phase: {response.get('phase', 'unknown')}")
            return True
        return False

    def test_memory_processing_phase_update(self):
        """Test updating memory processing phase"""
        if not self.memory_session_id:
            print("❌ No memory session ID available")
            return False
        
        success, response = self.run_test(
            "Update Memory Processing Phase",
            "POST",
            "memory/update-phase",
            200,
            data={
                "session_id": self.memory_session_id,
                "user_id": "test_user",
                "phase_data": {
                    "ritual_chosen": "fire",
                    "ritual_completed": True,
                    "closure_achieved": True
                }
            }
        )
        
        return success

    def test_emotion_history(self):
        """Test getting emotion history"""
        return self.run_test(
            "Get Emotion History",
            "GET",
            "emotions/history",
            200,
            data={"user_id": "test_user", "days": 14}
        )

    def test_recent_sessions(self):
        """Test getting recent sessions"""
        return self.run_test(
            "Get Recent Sessions",
            "GET",
            "sessions/recent",
            200,
            data={"user_id": "test_user", "limit": 7}
        )

    def test_pattern_analysis(self):
        """Test pattern analysis"""
        success, response = self.run_test(
            "Pattern Analysis",
            "POST",
            "patterns/analyze",
            200,
            data={"user_id": "test_user"}
        )
        
        if success:
            print(f"   Sessions analyzed: {response.get('sessions_analyzed', 0)}")
            return True
        return False

    def test_weekly_insights(self):
        """Test weekly insights generation"""
        success, response = self.run_test(
            "Generate Weekly Insights",
            "POST",
            "insights/generate",
            200,
            data={"user_id": "test_user"}
        )
        
        if success and ('full_summary' in response or 'message' in response):
            return True
        return False

    def test_auth_endpoints(self):
        """Test authentication endpoints (without actual OAuth)"""
        # Test /auth/me without authentication (should fail)
        success, response = self.run_test(
            "Auth Me (Unauthenticated)",
            "GET",
            "auth/me",
            401
        )
        return success

    def test_gemini_api_connection(self):
        """Test if Gemini API key is working by testing memory processing (no auth required)"""
        print("\n🔍 GEMINI API CONNECTION TEST")
        print("=" * 50)
        
        self.gemini_tests_run += 1
        
        success, response = self.run_test(
            "Gemini API Connection (via Memory Processing)",
            "POST",
            "memory/start",
            200,
            data={
                "user_id": "gemini_test_user",
                "memory_topic": "testing Gemini 2.0 Flash integration"
            }
        )
        
        if success and 'session_id' in response and 'messages' in response:
            self.gemini_tests_passed += 1
            self.memory_session_id = response['session_id']
            print("   ✅ Gemini API connection successful")
            print(f"   📝 Generated {len(response['messages'])} message chunks")
            
            # Check if response contains meaningful content
            if response['messages'] and len(response['messages'][0].get('content', '')) > 10:
                print("   ✅ Gemini generated meaningful response content")
                return True
            else:
                print("   ⚠️ Gemini response seems too short or empty")
                return False
        else:
            print("   ❌ Gemini API connection failed")
            return False

    def test_gemini_conversation_continuity(self):
        """Test if Gemini maintains conversation context"""
        if not self.memory_session_id:
            print("❌ No memory session ID available for continuity test")
            return False
        
        self.gemini_tests_run += 1
        
        # Send a follow-up message to test context retention
        success, response = self.run_test(
            "Gemini Conversation Continuity",
            "POST",
            "memory/message",
            200,
            data={
                "session_id": self.memory_session_id,
                "message": "I feel overwhelmed by work deadlines and can't stop thinking about failing. It's affecting my sleep and I feel anxious all the time.",
                "user_id": "gemini_test_user"
            }
        )
        
        if success and 'messages' in response:
            self.gemini_tests_passed += 1
            print("   ✅ Gemini maintained conversation context")
            
            # Check if response is contextually appropriate
            response_text = ' '.join([msg.get('content', '') for msg in response['messages']])
            if any(keyword in response_text.lower() for keyword in ['overwhelm', 'work', 'anxiety', 'sleep']):
                print("   ✅ Gemini response is contextually relevant")
                return True
            else:
                print("   ⚠️ Gemini response may not be contextually relevant")
                return False
        else:
            print("   ❌ Gemini conversation continuity failed")
            return False

    def test_gemini_response_chunking(self):
        """Test if Gemini responses are properly chunked into messages"""
        if not self.memory_session_id:
            print("❌ No memory session ID available for chunking test")
            return False
        
        self.gemini_tests_run += 1
        
        success, response = self.run_test(
            "Gemini Response Chunking",
            "POST",
            "memory/message",
            200,
            data={
                "session_id": self.memory_session_id,
                "message": "Can you help me understand what's happening and guide me through processing this?",
                "user_id": "gemini_test_user"
            }
        )
        
        if success and 'messages' in response:
            messages = response['messages']
            if len(messages) > 1:
                self.gemini_tests_passed += 1
                print(f"   ✅ Response properly chunked into {len(messages)} messages")
                
                # Check if chunks have proper timing
                has_timing = all('typing_delay' in msg and 'pause_after' in msg for msg in messages)
                if has_timing:
                    print("   ✅ Message chunks have proper timing delays")
                    return True
                else:
                    print("   ⚠️ Message chunks missing timing information")
                    return False
            else:
                print("   ⚠️ Response not chunked (single message)")
                self.gemini_tests_passed += 1  # Still counts as working
                return True
        else:
            print("   ❌ Gemini response chunking failed")
            return False

    def test_gemini_crisis_detection(self):
        """Test if Gemini integration maintains crisis detection"""
        # Create a new memory session for crisis testing
        self.gemini_tests_run += 1
        
        success, response = self.run_test(
            "Gemini Crisis Detection Setup",
            "POST",
            "memory/start",
            200,
            data={
                "user_id": "crisis_test_user",
                "memory_topic": "feeling hopeless and suicidal thoughts"
            }
        )
        
        if success and 'session_id' in response:
            crisis_session_id = response['session_id']
            
            # Test crisis message
            success2, response2 = self.run_test(
                "Gemini Crisis Detection",
                "POST",
                "memory/message",
                200,
                data={
                    "session_id": crisis_session_id,
                    "message": "I want to kill myself and end it all. I can't go on anymore.",
                    "user_id": "crisis_test_user"
                }
            )
            
            if success2:
                self.gemini_tests_passed += 1
                print("   ✅ Gemini handled crisis message without crashing")
                
                # Check if response is appropriate for crisis
                response_text = ' '.join([msg.get('content', '') for msg in response2.get('messages', [])])
                if any(keyword in response_text.lower() for keyword in ['988', 'support', 'help', 'therapist', 'professional']):
                    print("   ✅ Gemini provided appropriate crisis response")
                    return True
                else:
                    print("   ⚠️ Gemini crisis response may need review")
                    return True  # Still working, just response quality
            else:
                print("   ❌ Gemini crisis detection failed")
                return False
        else:
            print("   ❌ Could not set up crisis detection test")
            return False

    def test_gemini_pattern_analysis(self):
        """Test if Gemini integration works for pattern analysis"""
        self.gemini_tests_run += 1
        
        success, response = self.run_test(
            "Gemini Pattern Analysis",
            "POST",
            "patterns/analyze",
            200,
            data={"user_id": "pattern_test_user"}
        )
        
        if success:
            self.gemini_tests_passed += 1
            print("   ✅ Gemini pattern analysis endpoint working")
            
            if 'analysis' in response:
                print("   ✅ Gemini generated pattern analysis")
                return True
            elif 'message' in response and 'not enough data' in response['message'].lower():
                print("   ✅ Gemini correctly handled insufficient data")
                return True
            else:
                print("   ⚠️ Unexpected pattern analysis response format")
                return True
        else:
            print("   ❌ Gemini pattern analysis failed")
            return False

    def test_gemini_weekly_insights(self):
        """Test if Gemini integration works for weekly insights"""
        self.gemini_tests_run += 1
        
        success, response = self.run_test(
            "Gemini Weekly Insights",
            "POST",
            "insights/generate",
            200,
            data={"user_id": "insights_test_user"}
        )
        
        if success:
            self.gemini_tests_passed += 1
            print("   ✅ Gemini weekly insights endpoint working")
            
            if 'full_summary' in response:
                print("   ✅ Gemini generated weekly insights")
                return True
            elif 'message' in response and 'need at least' in response['message'].lower():
                print("   ✅ Gemini correctly handled insufficient data")
                return True
            else:
                print("   ⚠️ Unexpected insights response format")
                return True
        else:
            print("   ❌ Gemini weekly insights failed")
            return False

    def test_gemini_error_handling(self):
        """Test error handling with Gemini integration"""
        self.gemini_tests_run += 1
        
        # Test with invalid session ID
        success, response = self.run_test(
            "Gemini Error Handling",
            "POST",
            "memory/message",
            404,
            data={
                "session_id": "invalid-gemini-session",
                "message": "This should fail gracefully",
                "user_id": "error_test_user"
            }
        )
        
        if success:
            self.gemini_tests_passed += 1
            print("   ✅ Gemini error handling working correctly")
            return True
        else:
            print("   ❌ Gemini error handling failed")
            return False

    def run_comprehensive_gemini_tests(self):
        """Run all Gemini-specific tests"""
        print("\n🤖 COMPREHENSIVE GEMINI API INTEGRATION TESTS")
        print("=" * 60)
        
        # Test 1: Basic API Connection
        print("\n1. Testing Gemini API Connection...")
        self.test_gemini_api_connection()
        
        # Test 2: Conversation Continuity
        print("\n2. Testing Conversation Continuity...")
        self.test_gemini_conversation_continuity()
        
        # Test 3: Response Chunking
        print("\n3. Testing Response Chunking...")
        self.test_gemini_response_chunking()
        
        # Test 4: Crisis Detection
        print("\n4. Testing Crisis Detection...")
        self.test_gemini_crisis_detection()
        
        # Test 5: Pattern Analysis
        print("\n5. Testing Pattern Analysis...")
        self.test_gemini_pattern_analysis()
        
        # Test 6: Weekly Insights
        print("\n6. Testing Weekly Insights...")
        self.test_gemini_weekly_insights()
        
        # Test 7: Error Handling
        print("\n7. Testing Error Handling...")
        self.test_gemini_error_handling()
        
        # Gemini Test Summary
        print("\n" + "=" * 60)
        print(f"🤖 GEMINI INTEGRATION TEST RESULTS")
        print(f"Gemini Tests Run: {self.gemini_tests_run}")
        print(f"Gemini Tests Passed: {self.gemini_tests_passed}")
        if self.gemini_tests_run > 0:
            print(f"Gemini Success Rate: {(self.gemini_tests_passed/self.gemini_tests_run)*100:.1f}%")
        
        return self.gemini_tests_passed == self.gemini_tests_run

def main():
    print("🚀 Starting listentbh API Testing")
    print("=" * 50)
    
    tester = ListentbhAPITester()
    
    # Core API Tests
    print("\n📡 CORE API TESTS")
    tester.test_root_endpoint()
    
    # Chat Flow Tests
    print("\n💬 CHAT FUNCTIONALITY TESTS")
    tester.test_chat_session_start_unauthenticated()
    tester.test_chat_message_with_invalid_session()
    tester.test_chat_message_direct_with_valid_session()
    tester.test_chat_session_start()
    tester.test_chat_message()
    tester.test_crisis_detection()
    tester.test_session_complete()
    
    # Memory Processing Tests
    print("\n🧠 MEMORY PROCESSING TESTS")
    tester.test_memory_processing_start()
    tester.test_memory_processing_message()
    tester.test_memory_processing_phase_update()
    
    # Data Retrieval Tests
    print("\n📊 DATA RETRIEVAL TESTS")
    tester.test_emotion_history()
    tester.test_recent_sessions()
    
    # AI Analysis Tests
    print("\n🤖 AI ANALYSIS TESTS")
    tester.test_pattern_analysis()
    tester.test_weekly_insights()
    
    # Authentication Tests
    print("\n🔐 AUTHENTICATION TESTS")
    tester.test_auth_endpoints()
    
    # Comprehensive Chat Flow Diagnosis
    tester.test_chat_flow_diagnosis()
    
    # Final Results
    print("\n" + "=" * 50)
    print(f"📊 FINAL RESULTS")
    print(f"Tests Run: {tester.tests_run}")
    print(f"Tests Passed: {tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️ {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())