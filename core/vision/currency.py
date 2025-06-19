import requests, cv2
from collections import Counter


def calculate_currency(frame, save_path='data/currency.png', url='http://localhost:8000/detect/'):
    cv2.imwrite(save_path, frame)

    with open(save_path, 'rb') as f:
        files = {'file': (save_path, f, 'image/png')}
        try:
            response = requests.post(url, files=files, timeout=10)
            if response.status_code != 200:
                print(f"Server returned status code {response.status_code}")
                print(response.text)
                return None, None

            detections = response.json().get("detections", [])
            if not detections:
                return "No currency detected.", 0.0

            # Count occurrences of each class
            class_counts = Counter(det["class"] for det in detections)

            # Build summary string
            summary_parts = [f"{count} x {cls}" for cls, count in class_counts.items()]
            summary = ", ".join(summary_parts)

            # Calculate total value
            total = 0.0
            for cls, count in class_counts.items():
                try:
                    value = float(cls.split()[0])  # Get the numeric part
                    total += value * count
                except ValueError:
                    print(f"Could not parse currency value from class: {cls}")

            return summary, total

        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return None, None
