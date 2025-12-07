import argparse
import requests
import threading
import queue
import sys
import signal

requests.packages.urllib3.disable_warnings()

BANNER = r"""
   _  __        __      _       ____                          
  / |/ /____ __/ /_    (_)__   / __/______ ____  ___  ___ ____
 /    / -_) \ / __/   / (_-<  _\ \/ __/ _ `/ _ \/ _ \/ -_) __/
/_/|_/\__/_\_\\__(_)_/ /___/ /___/\__/\_,_/_//_/_//_/\__/_/   
                  |___/                                      
"""

NEXTJS_HEADER_KEYWORDS = [
    "next.js",
    "nextjs",
    "x-nextjs-page",
    "x-matched-path",
    "x-now-route-matches",
    "x-vercel-id",
    "x-vercel-cache",
    "x-nextjs-cache",
    "x-nextjs-stale-time"
]

stop_flag = False

def signal_handler(sig, frame):
    global stop_flag
    stop_flag = True
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


def check_nextjs(url, timeout):
    try:
        r = requests.get(url, timeout=timeout, verify=False)
        h = {k.lower(): v.lower() for k, v in r.headers.items()}
        for key, value in h.items():
            for kw in NEXTJS_HEADER_KEYWORDS:
                if kw in key or kw in value:
                    return True
        return False
    except:
        return False


def worker(q, timeout, outfile):
    while not q.empty() and not stop_flag:
        d = q.get()
        if not d.startswith("http"):
            d = "https://" + d

        result = check_nextjs(d, timeout)

        if result:
            line = d + "\n"
            outfile.write(line)
            outfile.flush()
            print(d, flush=True)

        q.task_done()


def main():
    parser = argparse.ArgumentParser(description="Next.js detector")
    parser.add_argument("-l", "--list", help="Domain list file")
    parser.add_argument("-u", "--url", help="Single target")
    parser.add_argument("-o", "--output", required=True, help="Output file")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Number of threads")
    parser.add_argument("--timeout", type=int, default=6, help="Request timeout")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    print(BANNER)

    targets = []

    if args.list:
        with open(args.list) as f:
            targets.extend([x.strip() for x in f if x.strip()])

    if args.url:
        targets.append(args.url.strip())

    if not targets:
        sys.exit(1)

    q = queue.Queue()
    for t in targets:
        q.put(t)

    outfile = open(args.output, "w")

    threads = []
    for _ in range(args.threads):
        th = threading.Thread(target=worker, args=(q, args.timeout, outfile))
        th.daemon = True
        th.start()
        threads.append(th)

    try:
        for th in threads:
            th.join()
    except KeyboardInterrupt:
        pass
    finally:
        outfile.close()


if __name__ == "__main__":
    main()
