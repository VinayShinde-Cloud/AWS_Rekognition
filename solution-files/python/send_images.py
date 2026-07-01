#!/usr/bin/env python3
"""
send_images.py — Send real vehicle images through the full pipeline.

Flow:
  This script → API Gateway → ImageGetAndSaveLambda → S3
                                                        ↓
                                             S3 event → SNS → SQS
                                                                ↓
                                               image_recognition Lambda
                                                                ↓
                                                 Rekognition DetectLabels
                                                                ↓
                                                         DynamoDB ✅

Cost estimate (Amazon Rekognition):
  $0.001 per image (first 1,000,000 images/month)
  10  images = $0.01
  50  images = $0.05
  100 images = $0.10
  500 images = $0.50

Usage:
  python send_images.py                        # interactive mode — asks how many
  python send_images.py --count 10             # send 10 images non-interactively
  python send_images.py --count 10 --delay 2   # 2 second delay between requests
  python send_images.py --dry-run              # show what would be sent, no API calls
"""

import argparse
import json
import os
import sys
import time

import requests
from requests.exceptions import RequestException

# ── Vehicle image pool ────────────────────────────────────────────────────────
# Free-to-use images from Pexels (no auth required, no rate limiting issues).
# Mix of cars, trucks, motorcycles, buses — realistic for a traffic use case.
IMAGE_POOL = [
    # Cars
    ("https://images.pexels.com/photos/1007410/pexels-photo-1007410.jpeg?w=640", "car-001.jpg"),
    ("https://images.pexels.com/photos/116675/pexels-photo-116675.jpeg?w=640",   "car-002.jpg"),
    ("https://images.pexels.com/photos/210019/pexels-photo-210019.jpeg?w=640",   "car-003.jpg"),
    ("https://images.pexels.com/photos/170811/pexels-photo-170811.jpeg?w=640",   "car-004.jpg"),
    ("https://images.pexels.com/photos/244206/pexels-photo-244206.jpeg?w=640",   "car-005.jpg"),
    ("https://images.pexels.com/photos/1545743/pexels-photo-1545743.jpeg?w=640", "car-006.jpg"),
    ("https://images.pexels.com/photos/3802510/pexels-photo-3802510.jpeg?w=640", "car-007.jpg"),
    ("https://images.pexels.com/photos/2127733/pexels-photo-2127733.jpeg?w=640", "car-008.jpg"),
    ("https://images.pexels.com/photos/1592384/pexels-photo-1592384.jpeg?w=640", "car-009.jpg"),
    ("https://images.pexels.com/photos/707046/pexels-photo-707046.jpeg?w=640",   "car-010.jpg"),
    # SUVs
    ("https://images.pexels.com/photos/1638459/pexels-photo-1638459.jpeg?w=640", "suv-001.jpg"),
    ("https://images.pexels.com/photos/2365572/pexels-photo-2365572.jpeg?w=640", "suv-002.jpg"),
    ("https://images.pexels.com/photos/3729464/pexels-photo-3729464.jpeg?w=640", "suv-003.jpg"),
    ("https://images.pexels.com/photos/1402787/pexels-photo-1402787.jpeg?w=640", "suv-004.jpg"),
    ("https://images.pexels.com/photos/3786091/pexels-photo-3786091.jpeg?w=640", "suv-005.jpg"),
    # Trucks
    ("https://images.pexels.com/photos/1427107/pexels-photo-1427107.jpeg?w=640", "truck-001.jpg"),
    ("https://images.pexels.com/photos/2199293/pexels-photo-2199293.jpeg?w=640", "truck-002.jpg"),
    ("https://images.pexels.com/photos/1223649/pexels-photo-1223649.jpeg?w=640", "truck-003.jpg"),
    # Motorcycles
    ("https://images.pexels.com/photos/2519374/pexels-photo-2519374.jpeg?w=640", "moto-001.jpg"),
    ("https://images.pexels.com/photos/1413412/pexels-photo-1413412.jpeg?w=640", "moto-002.jpg"),
    # Buses
    ("https://images.pexels.com/photos/1178448/pexels-photo-1178448.jpeg?w=640", "bus-001.jpg"),
    ("https://images.pexels.com/photos/2402235/pexels-photo-2402235.jpeg?w=640", "bus-002.jpg"),
    # Highway / traffic scenes
    ("https://images.pexels.com/photos/1004409/pexels-photo-1004409.jpeg?w=640", "highway-001.jpg"),
    ("https://images.pexels.com/photos/210182/pexels-photo-210182.jpeg?w=640",   "highway-002.jpg"),
    ("https://images.pexels.com/photos/1426516/pexels-photo-1426516.jpeg?w=640", "highway-003.jpg"),
]

MAX_POOL_SIZE = len(IMAGE_POOL)


def resolve_api_url() -> str:
    """
    Resolve the API Gateway URL automatically from cdk-outputs-APIStack.json.
    Falls back to asking the user if the file is not found.
    """
    outputs_file = os.path.join(os.path.dirname(__file__), "cdk-outputs-APIStack.json")
    if os.path.exists(outputs_file):
        with open(outputs_file) as f:
            outputs = json.load(f)
        # The API Gateway endpoint key ends with 'Endpoint...'
        api_stack = outputs.get("APIStack", {})
        for key, value in api_stack.items():
            if "Endpoint" in key and value.startswith("https://"):
                # Strip trailing slash
                return value.rstrip("/")
    return ""


def cost_estimate(count: int) -> str:
    cost = count * 0.001
    return f"${cost:.3f}"


def send_image(api_url: str, image_url: str, name: str, dry_run: bool) -> bool:
    """
    Send one image through the API Gateway pipeline.
    Returns True on success, False on failure.
    """
    if dry_run:
        print(f"  [DRY RUN] Would call: {api_url}?url={image_url}&name={name}")
        return True

    try:
        response = requests.get(
            api_url,
            params={"url": image_url, "name": name},
            timeout=15,
        )
        if response.status_code == 200:
            return True
        else:
            print(f"  ✗ HTTP {response.status_code}: {response.text}")
            return False
    except RequestException as e:
        print(f"  ✗ Request error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Send vehicle images through the Rekognition pipeline via API Gateway"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Number of images to send (max 25, default: interactive prompt)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between requests (default: 1.0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be sent without making any API calls",
    )
    parser.add_argument(
        "--api-url",
        default=None,
        help="API Gateway URL (auto-resolved from cdk-outputs-APIStack.json if omitted)",
    )
    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║   Cloudage — Vehicle Image Pipeline                  ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    # ── Resolve API URL ────────────────────────────────────────────────────────
    api_url = args.api_url or resolve_api_url()
    if not api_url:
        print("Could not auto-resolve API Gateway URL from cdk-outputs-APIStack.json.")
        api_url = input("Enter your API Gateway URL: ").strip().rstrip("/")
        if not api_url:
            print("Error: API URL is required.")
            sys.exit(1)

    print(f"  API URL : {api_url}")
    print(f"  Pool    : {MAX_POOL_SIZE} unique vehicle images available")
    print()

    # ── Ask how many images ────────────────────────────────────────────────────
    if args.count is not None:
        count = args.count
    else:
        print("  Rekognition cost: $0.001 per image")
        print(f"  {'Count':<8} {'Est. Cost':<12} {'Note'}")
        print(f"  {'─'*8} {'─'*12} {'─'*30}")
        for n, note in [(5, "quick test"), (10, "good demo"), (25, "full pool")]:
            print(f"  {n:<8} {cost_estimate(n):<12} {note}")
        print()

        while True:
            try:
                raw = input(f"  How many images to send? (1–{MAX_POOL_SIZE}, default 10): ").strip()
                count = int(raw) if raw else 10
                if 1 <= count <= MAX_POOL_SIZE:
                    break
                print(f"  Please enter a number between 1 and {MAX_POOL_SIZE}.")
            except ValueError:
                print("  Please enter a valid number.")

    # ── Confirm ────────────────────────────────────────────────────────────────
    print()
    print(f"  Images to send : {count}")
    print(f"  Estimated cost : {cost_estimate(count)} (Rekognition DetectLabels)")
    print(f"  Delay          : {args.delay}s between requests")
    if args.dry_run:
        print("  Mode           : DRY RUN — no API calls will be made")
    print()

    if not args.dry_run:
        confirm = input("  Proceed? (yes/no, default yes): ").strip().lower()
        if confirm not in ("", "yes", "y"):
            print("  Aborted.")
            sys.exit(0)

    print()

    # ── Send images ────────────────────────────────────────────────────────────
    # Cycle through the pool if count > pool size
    images_to_send = []
    for i in range(count):
        url, name_base = IMAGE_POOL[i % MAX_POOL_SIZE]
        # Add index suffix if cycling to avoid S3 key conflicts
        if count > MAX_POOL_SIZE:
            stem, ext = name_base.rsplit(".", 1)
            name = f"{stem}-{i+1:03d}.{ext}"
        else:
            name = name_base
        images_to_send.append((url, name))

    success = 0
    failed = 0

    for i, (image_url, name) in enumerate(images_to_send, 1):
        print(f"  [{i:>3}/{count}] {name}", end=" ... ", flush=True)
        ok = send_image(api_url, image_url, name, args.dry_run)
        if ok:
            print("✓")
            success += 1
        else:
            failed += 1

        # Delay between requests (skip after last one)
        if i < count and args.delay > 0 and not args.dry_run:
            time.sleep(args.delay)

    # ── Summary ────────────────────────────────────────────────────────────────
    print()
    print(f"  ✓ Sent successfully : {success}")
    if failed:
        print(f"  ✗ Failed            : {failed}")
    print(f"  Estimated cost      : {cost_estimate(success)}")
    print()
    print("  Pipeline is processing — wait ~30 seconds then check DynamoDB:")
    print("    python scan_classifications.py")
    print()


if __name__ == "__main__":
    main()
