import httpx
import asyncio
import json

async def test_generate():
    url = "http://localhost:8080/generate"
    payload = {"username": "Shub-ways"}
    
    print(f"Requesting card generation for 'Shub-ways' at {url}...")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                print("\n✅ Generation Successful!")
                print(f"Card URL: http://localhost:8080{data['card_url']}")
                # print(f"HTML Length: {len(data['html'])} characters")
            else:
                print(f"\n❌ Generation Failed: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    # Wait a bit for server to start
    import time
    time.sleep(5)
    asyncio.run(test_generate())
