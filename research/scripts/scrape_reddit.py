from dotenv import load_dotenv
import os
import neptune
import praw
from datetime import datetime
from utils.file_utils import save_progress, load_progress, save_final_csv
from utils.reddit_helpers import reddit_connect, track_scraping_metrics
import time
import pandas as pd
from tqdm import tqdm
import sys

from pathlib import Path
Root = Path('.').absolute().parent
SCRIPTS = Root / r'C:\Users\krishnadas\Projects\ML Projects\ManipDetect\research\scripts'
DATA = Root/ r'C:\Users\krishnadas\Projects\ML Projects\ManipDetect\data'

def build_dataset(reddit, target_posts=10):
    """Build the dataset by scraping WallStreetBetsnew posts"""
    
    # Load previous progress
    filepath = SCRIPTS/'temp_data'  # Define the path to save progress
    posts_data, last_post_id = load_progress()
    start_count = len(posts_data)
    
    if start_count > 0:
        print(f"Resuming from {start_count} previously scraped posts...")
    else:
        print("Starting fresh scrape...")
    
    # Get subreddit
    # subreddit = reddit.subreddit("wallstreetbets")
    # change to new subreddit
    subreddit = reddit.subreddit("wallstreetbetsnew")

    
    # Track scraping metrics
    start_time = time.time()
    errors_count = 0
    
    try:
        # Get posts (PRAW handles pagination automatically)
        posts_generator = subreddit.new(limit=target_posts)
        
        # Convert to list to get total count for progress bar
        print("Fetching post list from Reddit...")
        all_posts = list(posts_generator)
        
        # Skip posts we already have if resuming
        if last_post_id:
            # Find where to resume
            resume_index = 0
            for i, post in enumerate(all_posts):
                if post.id == last_post_id:
                    resume_index = i + 1
                    break
            all_posts = all_posts[resume_index:]
            print(f"Resuming from post index {resume_index}")
        
        # Process remaining posts
        posts_to_process = min(len(all_posts), target_posts - start_count)
        
        for i, submission in enumerate(tqdm(all_posts[:posts_to_process], 
                                        desc="Scraping posts", 
                                        initial=start_count, 
                                        total=target_posts)):
            try:
                # Handle author safely
                author_name = "[deleted]"
                author_id = None
                if submission.author is not None:
                    try:
                        author_name = submission.author.name
                        author_id = submission.author.id
                    except Exception:
                        author_name = "[unavailable]"
                        author_id = None
                
                # Extract post text content with better categorization
                post_text = ""
                post_type = "text"  # Default type
                
                if submission.is_self:  # Text post
                    if submission.selftext:
                        post_text = submission.selftext
                        post_type = "text"
                    else:
                        post_text = "[Empty text post]"
                        post_type = "text_empty"
                else:  # Link post
                    post_text = "[Link Post]"
                    post_type = "link"
                    
                    # You could also categorize by URL type
                    if any(img_ext in submission.url.lower() for img_ext in ['.jpg', '.jpeg', '.png', '.gif']):
                        post_type = "image"
                    elif 'youtube.com' in submission.url.lower() or 'youtu.be' in submission.url.lower():
                        post_type = "video"
                
                # Extract post data (keeping titles and emojis intact)
                post_info = {
                    "post_id": submission.id,
                    "title": submission.title,  # Preserves emojis and formatting
                    "text": post_text,  # The actual post content
                    "post_type": post_type,  # Type of post for analysis
                    "author_name": author_name,  # Author's name
                    "author_id": author_id,  # Author's ID
                    "score": submission.score,
                    "created_utc": submission.created_utc,
                    "num_comments": submission.num_comments,
                    "url": submission.url,
                }
                
                posts_data.append(post_info)
                
                # Save progress every 50 posts
                if (len(posts_data) - start_count) % 50 == 0:
                    save_progress(posts_data, submission.id)
                
                # Small delay every 100 posts to be nice to Reddit
                if (len(posts_data) - start_count) % 100 == 0:
                    time.sleep(1)
                    
            except Exception as e:
                errors_count += 1
                print(f"Error processing post {submission.id}: {str(e)}")
                continue
        
        # Final save
        save_progress(posts_data, posts_data[-1]["post_id"] if posts_data else None)
        
        # Calculate final metrics
        end_time = time.time()
        scraping_duration = end_time - start_time
        
        # Save final CSV dataset
        csv_filename = save_final_csv(posts_data, filepath)
        
        # Return metrics for tracking
        metrics = {
            'total_posts_collected': len(posts_data),
            'new_posts_this_session': len(posts_data) - start_count,
            'scraping_duration_minutes': scraping_duration / 60,
            'errors_encountered': errors_count,
            'posts_per_minute': (len(posts_data) - start_count) / (scraping_duration / 60) if scraping_duration > 0 else 0,
            'csv_filename': str(csv_filename),
            'total_posts_available': len(all_posts),
            'resumed_from': start_count if start_count > 0 else None
        }
        
        print(f"\nDataset building completed!")
        print(f"Total posts collected: {metrics['total_posts_collected']}")
        print(f"New posts this session: {metrics['new_posts_this_session']}")
        print(f"Duration: {metrics['scraping_duration_minutes']:.2f} minutes")
        print(f"Errors: {metrics['errors_encountered']}")
        
        return posts_data, metrics
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user. Progress saved.")
        save_progress(posts_data, posts_data[-1]["post_id"] if posts_data else None)
        return posts_data, {'interrupted': True, 'posts_at_interruption': len(posts_data)}
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        save_progress(posts_data, posts_data[-1]["post_id"] if posts_data else None)
        return posts_data, {'fatal_error': str(e), 'posts_at_error': len(posts_data)}


def scrape_wallstreetbetsnew():
    """Main function that orchestrates the scraping process"""
    # Build the dataset
    reddit = reddit_connect()
    print("Connected to Reddit API successfully.")
    posts_data, metrics = build_dataset(reddit, target_posts)
    
    # Track metrics in Neptune
    track_scraping_metrics(posts_data, metrics, target_posts)
    
    return posts_data, metrics

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('Usage: scrape_reddit.py target_posts')
        sys.exit(1)
    target_posts = int(sys.argv[1])
    scrape_wallstreetbetsnew()
