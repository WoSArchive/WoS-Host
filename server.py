from waitress import serve
from core.wsgi import application  # Update path if your WSGI module is elsewhere
import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Starting server on http://0.0.0.0:80")
    serve(
        application,
        host="0.0.0.0",
        port=80,
        threads=8,               # More concurrency for better performance
        connection_limit=1000,   # Optional: Raise limit if expecting traffic
        backlog=128              # Optional: Max queue of incoming connections
    )
