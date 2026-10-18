import argparse
import os

from waitress import serve


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webconfig.settings")
    from webconfig.wsgi import application

    print(f"FinanceTracker: http://{args.host}:{args.port}", flush=True)
    serve(application, host=args.host, port=args.port, threads=4,
          max_request_body_size=16384, expose_tracebacks=False)
