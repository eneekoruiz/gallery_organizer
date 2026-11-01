import concurrent.futures

# Global thread pool for background tasks
task_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

def run_background_task(func, *args, **kwargs):
    """Submit a function to run in the background."""
    return task_executor.submit(func, *args, **kwargs)
