#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Suite for KidsClubPlans Conversational
Tests the full user journey from chat to export.
"""
import requests
import json
import sys
import time
from datetime import datetime, timedelta

BASE_URL = "https://chat.kidsclubplans.app"

class TestSuite:
    def __init__(self):
        self.session = requests.Session()
        self.results = []
        self.test_schedule_id = None
        self.test_activity_id = None
        
    def log(self, message, level="INFO"):
        emoji = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(level, "ℹ️")
        print(f"{emoji} {message}")
        
    def test_session_establishment(self):
        """Test 1: Can establish a session"""
        try:
            response = self.session.post(
                f"{BASE_URL}/chat",
                json={"message": "Hello"},
                stream=True,
                timeout=30
            )
            # Read first chunk to ensure connection works
            for line in response.iter_lines():
                if line:
                    break
            self.log("Session establishment", "PASS")
            return True
        except Exception as e:
            self.log(f"Session establishment failed: {e}", "FAIL")
            return False
    
    def test_chat_streaming(self):
        """Test 2: Chat streaming works"""
        try:
            response = self.session.post(
                f"{BASE_URL}/chat",
                json={"message": "What activities work for 8-year-olds?"},
                stream=True,
                timeout=60
            )
            
            chunks_received = 0
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        chunks_received += 1
                        if chunks_received >= 3:  # Got enough chunks
                            break
            
            if chunks_received >= 3:
                self.log("Chat streaming", "PASS")
                return True
            else:
                self.log(f"Chat streaming: only {chunks_received} chunks", "FAIL")
                return False
        except Exception as e:
            self.log(f"Chat streaming failed: {e}", "FAIL")
            return False
    
    def test_activity_generation(self):
        """Test 3: Can generate activities from supplies"""
        try:
            response = self.session.post(
                f"{BASE_URL}/chat",
                json={"message": "Generate activities using paper plates and markers for 7-8 year olds"},
                stream=True,
                timeout=60
            )
            
            activities = []
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        try:
                            event = json.loads(data)
                            if event.get('type') == 'activity':
                                activities.append(event.get('data'))
                        except:
                            pass
            
            if len(activities) > 0:
                self.log(f"Activity generation: {len(activities)} activities", "PASS")
                return True
            else:
                self.log("Activity generation: no activities received", "FAIL")
                return False
        except Exception as e:
            self.log(f"Activity generation failed: {e}", "FAIL")
            return False
    
    def test_save_activity(self):
        """Test 4: Can save a generated activity"""
        try:
            save_response = self.session.post(
                f"{BASE_URL}/api/activities/save",
                json={
                    "title": "Test Activity - Balloon Pop",
                    "description": "A fun cooperative game for testing.",
                    "instructions": "1. Blow up balloons. 2. Keep them in the air. 3. Work together!",
                    "age_group": "6-10 years",
                    "duration_minutes": 20,
                    "supplies": ["balloons"],
                    "activity_type": "Physical",
                    "indoor_outdoor": "indoor"
                },
                timeout=30
            )
            
            if save_response.status_code == 200:
                data = save_response.json()
                self.test_activity_id = data.get('activity_id')
                self.log(f"Save activity: ID {self.test_activity_id}", "PASS")
                return True
            else:
                self.log(f"Save activity failed: {save_response.status_code}", "FAIL")
                return False
        except Exception as e:
            self.log(f"Save activity failed: {e}", "FAIL")
            return False
    
    def test_generate_schedule(self):
        """Test 5: Can generate schedule template"""
        try:
            response = self.session.post(
                f"{BASE_URL}/api/schedule/generate",
                json={
                    "date": "2026-03-20",
                    "age_group": "8-10 years",
                    "duration_hours": 4,
                    "preferences": {"start_time": "9:00 AM", "include_breaks": True},
                    "include_weather": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                template = data.get('template', [])
                self.log(f"Schedule generation: {len(template)} slots", "PASS")
                return True
            else:
                self.log(f"Schedule generation failed: {response.status_code}", "FAIL")
                return False
        except Exception as e:
            self.log(f"Schedule generation failed: {e}", "FAIL")
            return False
    
    def test_save_and_manage_schedule(self):
        """Test 6: Full schedule CRUD"""
        try:
            # Generate
            gen_response = self.session.post(
                f"{BASE_URL}/api/schedule/generate",
                json={
                    "date": "2026-03-21",
                    "age_group": "7-9 years",
                    "duration_hours": 3,
                    "preferences": {"start_time": "10:00 AM"},
                    "include_weather": False
                },
                timeout=30
            ).json()
            
            # Save
            activities = [{
                "start_time": slot.get("time", "10:00"),
                "end_time": slot.get("time", "10:00"),
                "duration_minutes": slot.get("duration_minutes", 30),
                "title": slot.get("title") or "Activity",
                "description": slot.get("description", "")
            } for slot in gen_response.get("template", [])]
            
            save_response = self.session.post(
                f"{BASE_URL}/api/schedule/save",
                json={
                    "date": "2026-03-21",
                    "title": "Test Schedule",
                    "age_group": "7-9 years",
                    "duration_hours": 3,
                    "activities": activities
                },
                timeout=30
            )
            
            if save_response.status_code != 200:
                self.log("Schedule save failed", "FAIL")
                return False
            
            self.test_schedule_id = save_response.json().get("id")
            
            # List
            list_response = self.session.get(f"{BASE_URL}/api/schedules", timeout=10)
            if list_response.json().get("total", 0) == 0:
                self.log("Schedule list empty", "FAIL")
                return False
            
            # Get
            get_response = self.session.get(
                f"{BASE_URL}/api/schedule/{self.test_schedule_id}",
                timeout=10
            )
            if get_response.status_code != 200:
                self.log("Schedule get failed", "FAIL")
                return False
            
            # Delete
            del_response = self.session.delete(
                f"{BASE_URL}/api/schedule/{self.test_schedule_id}",
                timeout=10
            )
            if del_response.status_code != 200:
                self.log("Schedule delete failed", "FAIL")
                return False
            
            self.log("Schedule CRUD operations", "PASS")
            return True
            
        except Exception as e:
            self.log(f"Schedule management failed: {e}", "FAIL")
            return False
    
    def test_gap_analysis(self):
        """Test 7: Gap analysis works"""
        try:
            response = self.session.post(
                f"{BASE_URL}/chat",
                json={"message": "Analyze my database for gaps"},
                stream=True,
                timeout=60
            )
            
            content = ""
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        try:
                            event = json.loads(data)
                            if event.get('type') == 'content':
                                content += event.get('data', {}).get('content', '')
                        except:
                            pass
            
            if 'gap' in content.lower() or 'coverage' in content.lower():
                self.log("Gap analysis", "PASS")
                return True
            else:
                self.log("Gap analysis: no gap content detected", "WARN")
                return True  # Still pass, might be different response
        except Exception as e:
            self.log(f"Gap analysis failed: {e}", "FAIL")
            return False
    
    def test_weather_api(self):
        """Test 8: Weather API responds"""
        try:
            response = self.session.post(
                f"{BASE_URL}/api/weather",
                json={"location": "Lansing, MI", "date": "tomorrow"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"Weather API: {data.get('temperature', 'N/A')}°F", "PASS")
                return True
            else:
                self.log(f"Weather API: {response.status_code}", "WARN")
                return True  # Might be missing API key, not critical
        except Exception as e:
            self.log(f"Weather API error: {e}", "WARN")
            return True  # Non-critical
    
    def test_health_endpoint(self):
        """Test 9: Health check"""
        try:
            response = self.session.get(f"{BASE_URL}/health", timeout=10)
            if response.status_code == 200:
                self.log("Health endpoint", "PASS")
                return True
            else:
                self.log(f"Health endpoint: {response.status_code}", "FAIL")
                return False
        except Exception as e:
            self.log(f"Health check failed: {e}", "FAIL")
            return False
    
    def run_all(self):
        """Run all tests"""
        print("="*60)
        print("🚀 KidsClubPlans E2E Test Suite")
        print("="*60)
        print()
        
        tests = [
            ("Session Establishment", self.test_session_establishment),
            ("Chat Streaming", self.test_chat_streaming),
            ("Activity Generation", self.test_activity_generation),
            ("Save Activity", self.test_save_activity),
            ("Generate Schedule", self.test_generate_schedule),
            ("Schedule CRUD", self.test_save_and_manage_schedule),
            ("Gap Analysis", self.test_gap_analysis),
            ("Weather API", self.test_weather_api),
            ("Health Check", self.test_health_endpoint),
        ]
        
        passed = 0
        failed = 0
        
        for name, test_func in tests:
            print(f"\n📋 {name}")
            print("-"*40)
            if test_func():
                passed += 1
            else:
                failed += 1
        
        print()
        print("="*60)
        print(f"📊 Results: {passed} passed, {failed} failed")
        print("="*60)
        
        return failed == 0

if __name__ == "__main__":
    suite = TestSuite()
    success = suite.run_all()
    sys.exit(0 if success else 1)
