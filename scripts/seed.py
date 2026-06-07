#!/usr/bin/env python3
"""
seed.py — Submit sample jobs to TaskForge via the API.
Usage:  python scripts/seed.py [--host http://localhost:8000] [--count 20]
"""
import argparse
import random
import httpx

REPORT_TYPES = ["monthly_sales", "user_activity", "inventory_turnover", "churn_analysis"]
SUBJECTS = ["Welcome!", "Invoice #12345", "Password Reset", "Your order has shipped", "Action required"]

def seed(host: str, count: int):
    client = httpx.Client(base_url=host, timeout=10)

    for i in range(count):
        task = random.choice(["email", "image", "report"])

        if task == "email":
            r = client.post("/jobs/email", json={
                "to": f"user{i}@example.com",
                "subject": random.choice(SUBJECTS),
                "body": f"Hello user {i}, this is a test message from TaskForge.",
                "priority": random.randint(1, 10),
            })

        elif task == "image":
            r = client.post("/jobs/image-resize", json={
                "image_url": f"https://picsum.photos/seed/{i}/1920/1080",
                "width": random.choice([320, 640, 800, 1280]),
                "height": random.choice([240, 480, 600, 720]),
                "format": random.choice(["JPEG", "PNG", "WEBP"]),
                "priority": random.randint(1, 10),
            })

        else:
            r = client.post("/jobs/report", json={
                "report_type": random.choice(REPORT_TYPES),
                "parameters": {
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                    "region": random.choice(["APAC", "EMEA", "AMER"]),
                },
                "priority": random.randint(1, 10),
            })

        if r.status_code == 202:
            data = r.json()
            print(f"  ✓ [{data['type']:12}] {data['id'][:8]}... → {data['status']}")
        else:
            print(f"  ✗ Failed: {r.status_code} {r.text}")

    print(f"\nSeeded {count} jobs. View at {host}/docs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8000")
    parser.add_argument("--count", type=int, default=20)
    args = parser.parse_args()
    print(f"Seeding {args.count} jobs to {args.host}...\n")
    seed(args.host, args.count)
