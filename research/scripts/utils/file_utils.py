from datetime import datetime
import json
import pandas as pd

def load_progress(filename="scraping_progress.json"):
    """Load previously scraped data if it exists"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            posts = data.get('posts', [])
            
            # Normalize old data structure to ensure consistency
            consistent_posts = []
            for post in posts:
                # Ensure all required fields exist with default values
                consistent_post_dict = {
                    'post_id': post.get('post_id', ''),
                    'title': post.get('title', ''),
                    'text': post.get('text', post.get('selftext', '')),  # Handle old 'selftext' field
                    'post_type': post.get('post_type', 'unknown'),
                    'author_name': post.get('author_name', post.get('author', '[unknown]')),  # Handle old 'author' field
                    'author_id':post.get('author_id', post.get('author_id', '')),
                    'score': post.get('score', 0),
                    'num_comments': post.get('num_comments', 0),
                    'created_utc': post.get('created_utc', 0),
                    'url': post.get('url', '')
                }
                consistent_posts.append(consistent_post_dict)
            scraped_ids = [post.get('post_id') for post in consistent_posts]
            return consistent_posts, scraped_ids
    except FileNotFoundError:
        return [], set()

def save_progress(posts_data, scraped_ids, filename="scraping_progress.json"):
    """Save current progress to file"""
    progress_data = {
        'posts': posts_data,
        'scraped_ids': scraped_ids,
        'saved_at': datetime.now().isoformat(),
        'total_posts': len(posts_data)
    }
    # Save progress as JSON (for resume functionality)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(progress_data, f, ensure_ascii=False, indent=2)
    
    # Also save current data as CSV
    if posts_data:
        df = pd.DataFrame(posts_data)
        df.to_csv("wallstreetbetsnew_posts.csv", index=False, encoding='utf-8')

def save_final_csv(posts_data, filepath):
    """Save final dataset as CSV with proper formatting"""
    if not posts_data:
        return
    df = pd.DataFrame(posts_data)
    
    # Convert timestamp to readable format
    df['created_datetime'] = pd.to_datetime(df['created_utc'], unit='s')
    
    # Reorder columns for better readability, but only use columns that exist
    preferred_columns_order = ['post_id', 'title', 'text', 'post_type', 'author_name', 'author_id', 'score', 'num_comments', 
                                'created_utc', 'url']
    
    # Filter to only include columns that actually exist in the DataFrame
    available_columns = [col for col in preferred_columns_order if col in df.columns]
    
    # Add any remaining columns that weren't in our preferred order
    remaining_columns = [col for col in df.columns if col not in available_columns]
    final_columns_order = available_columns + remaining_columns
    
    df = df[final_columns_order]
    
    # Save with timestamp in filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # csv_filename = f"wallstreetbetsnew_posts_{timestamp}.csv"
    csv_filename = filepath / f"wallstreetbetsnew_posts_{timestamp}.csv"
    df.to_csv(csv_filename, index=False, encoding='utf-8')
    
    return csv_filename