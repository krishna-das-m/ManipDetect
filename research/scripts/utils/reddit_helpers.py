from dotenv import load_dotenv
import os
import neptune
import praw
from datetime import datetime

def reddit_connect():
    """Initialize Reddit connection"""
    load_dotenv()
    reddit = praw.Reddit(
        client_id=os.getenv('REDDIT_CLIENT_ID'),
        client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
        user_agent=os.getenv('REDDIT_USER_AGENT'),
        username=os.getenv('REDDIT_USERNAME'),
        password=os.getenv('REDDIT_PASSWORD')
    )
    return reddit


def track_scraping_metrics(posts_data, metrics, target_posts):
    """Track scraping metrics and results in Neptune"""
    # Initialize Neptune
    run = neptune.init_run(project="krishnadasm/wallstreetbets-scraper")
    
    # Log configuration
    run["config/target_posts"] = target_posts
    run["config/subreddit"] = "wallstreetbetsnew"
    run["config/sort_method"] = "new"
    run["config/resume_enabled"] = True
    
    # Log scraping metrics
    if 'interrupted' in metrics:
        run["scraping/interrupted"] = True
        run["scraping/posts_at_interruption"] = metrics['posts_at_interruption']
    elif 'fatal_error' in metrics:
        run["scraping/fatal_error"] = metrics['fatal_error']
        run["scraping/posts_at_error"] = metrics['posts_at_error']
    else:
        # Log successful completion metrics
        run["results/total_posts_collected"] = metrics['total_posts_collected']
        run["results/new_posts_this_session"] = metrics['new_posts_this_session']
        run["results/scraping_duration_minutes"] = metrics['scraping_duration_minutes']
        run["results/errors_encountered"] = metrics['errors_encountered']
        run["results/posts_per_minute"] = metrics['posts_per_minute']
        run["scraping/total_posts_available"] = metrics['total_posts_available']
        
        if metrics['resumed_from']:
            run["scraping/resumed_from"] = metrics['resumed_from']
        
        # Upload final dataset to Neptune
        if metrics.get('csv_filename'):
            run["data/posts_dataset"].upload(metrics['csv_filename'])
        run["data/progress_file"].upload("scraping_progress.json")
    
    # Log final progress
    run["scraping/final_progress"] = len(posts_data)
    
    run.stop()
    print("Metrics logged to Neptune successfully!")
