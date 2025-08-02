#!/usr/bin/env python3
"""
Script to create a test post with status for testing the UI
"""

import asyncio
import uuid
from datetime import datetime
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def create_test_post():
    """Create a test post with status directly in the database"""
    
    # Database connection
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/civicpulse")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        # First, let's check if we have any users
        users = await conn.fetch("SELECT id, username FROM users LIMIT 5")
        if not users:
            print("No users found. Creating a test user first...")
            
            # Create a test user
            user_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO users (id, username, email, password_hash, display_name, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, user_id, "testuser", "test@example.com", "dummy_hash", "Test User", datetime.utcnow(), datetime.utcnow())
            
            print(f"Created test user: {user_id}")
        else:
            user_id = str(users[0]['id'])
            print(f"Using existing user: {users[0]['username']} ({user_id})")
        
        # Check if we have any representatives for assignee
        reps = await conn.fetch("SELECT id, cached_name FROM representatives LIMIT 5")
        assignee_id = str(reps[0]['id']) if reps else None
        
        if assignee_id:
            print(f"Using representative: {reps[0]['cached_name']} ({assignee_id})")
        else:
            print("No representatives found - creating post without assignee")
        
        # Create test posts with different statuses
        test_posts = [
            {
                "title": "Road Repair Needed on Main Street",
                "content": "There are several potholes on Main Street that need immediate attention. This is causing traffic issues and potential vehicle damage.",
                "post_type": "issue",
                "status": "open"
            },
            {
                "title": "Community Garden Project Update",
                "content": "The community garden project is making good progress. We've completed the soil preparation and are now working on installing irrigation.",
                "post_type": "accomplishment", 
                "status": "in_progress"
            },
            {
                "title": "Street Light Installation Complete",
                "content": "The new street lights on Oak Avenue have been successfully installed and are now operational. Thank you for your patience during the construction.",
                "post_type": "announcement",
                "status": "resolved"
            },
            {
                "title": "Park Renovation Project",
                "content": "The park renovation project has been completed successfully. All new equipment is installed and the park is ready for public use.",
                "post_type": "accomplishment",
                "status": "closed"
            }
        ]
        
        created_posts = []
        
        for post_data in test_posts:
            post_id = str(uuid.uuid4())
            
            await conn.execute("""
                INSERT INTO posts (
                    id, user_id, title, content, post_type, status, assignee,
                    upvotes, downvotes, comment_count, view_count, share_count,
                    priority_score, created_at, updated_at, last_activity_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            """, 
                post_id, user_id, post_data["title"], post_data["content"],
                post_data["post_type"], post_data["status"], assignee_id,
                0, 0, 0, 0, 0, 0,  # counts
                datetime.utcnow(), datetime.utcnow(), datetime.utcnow()
            )
            
            created_posts.append({
                "id": post_id,
                "title": post_data["title"],
                "status": post_data["status"]
            })
            
            print(f"✅ Created post: {post_data['title']} (Status: {post_data['status']})")
        
        print(f"\n🎉 Successfully created {len(created_posts)} test posts with different statuses!")
        print("\nYou can now:")
        print("1. Refresh your browser at http://localhost:3002")
        print("2. Log in with a test account")
        print("3. See posts with status badges")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Creating test posts with status...")
    success = asyncio.run(create_test_post())
    if success:
        print("\n✅ Test posts created successfully!")
    else:
        print("\n❌ Failed to create test posts")
