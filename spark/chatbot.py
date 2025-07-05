import os
import re
import requests
from collections import defaultdict
from dotenv import load_dotenv




import os
import re
import requests
from collections import defaultdict
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Get API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# Error check
if not OPENAI_API_KEY or not SERPAPI_KEY:
    raise EnvironmentError("Missing API keys in .env")

# Initialize OpenAI client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENAI_API_KEY,
    default_headers={
        "HTTP-Referer": os.getenv("APP_URL", "https://sparkathon.onrender.com"),
        "X-Title": os.getenv("APP_NAME", "Walmart Assistant")
    }
)

def search_walmart(query):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": SERPAPI_KEY,
        "store": "walmart"
    }
    try:
        res = requests.get(url, params=params, timeout=15)
        res.raise_for_status()
        data = res.json()
        return data.get("shopping_results", [])[:3]
    except Exception as e:
        return f"❌ Error: {str(e)}"

def is_product_query(text):
    keywords = ["buy", "search", "product", "find", "price", "cost", "deal", "shop", "walmart", "order", "get"]
    return any(k in text.lower() for k in keywords)

def get_bot_response(user_message, state=None):
    user_message = user_message.strip()
    state = state or {'cart': {}, 'product_lookup': {}, 'last_products': []}
    cart = defaultdict(int, state.get('cart', {}))
    product_lookup = state.get('product_lookup', {})
    last_products = state.get('last_products', [])

    # Handle add to cart
    add_match = re.match(r"add to cart (\d+)", user_message.lower())
    if add_match:
        idx = int(add_match.group(1)) - 1
        if 0 <= idx < len(last_products):
            product = last_products[idx]
            pid = product.get('product_id') or product.get('position')
            if pid:
                cart[pid] += 1
                product_lookup[pid] = product
                state.update(cart=dict(cart), product_lookup=product_lookup)
                return f"✅ Added **{product.get('title', 'Unknown')}** to your cart!", state
        return "❌ Invalid product number.", state

    # Handle cart viewing
    if user_message.lower() in ["show cart", "view cart", "cart"]:
        if not cart:
            return "🛒 Your cart is empty.", state
        response = "**Your cart:**\n"
        total = 0
        for pid, qty in cart.items():
            product = product_lookup.get(pid)
            if not product:
                continue
            price = float(product.get("price", 0))
            subtotal = price * qty
            total += subtotal
            response += f"- {product.get('title', 'Unknown')}: ${price:.2f} × {qty} = ${subtotal:.2f}\n"
        response += f"\n**Total: ${total:.2f}**"
        return response, state

    if user_message.lower() == "clear cart":
        state.update(cart={}, product_lookup={})
        return "🧹 Cart cleared!", state

    # Product search
    if is_product_query(user_message):
        results = search_walmart(user_message)
        if isinstance(results, str):
            return results, state  # Error message

        if not results:
            return "🙇‍♂️ No products found.", state

        # Save results
        state['last_products'] = results
        for p in results:
            pid = p.get('product_id') or p.get('position')
            if pid:
                product_lookup[pid] = p
        state['product_lookup'] = product_lookup

        # Build response
        response = "**🔍 Top Products:**\n\n"
        for i, p in enumerate(results, 1):
            title = p.get("title", "No title")
            price = p.get("price", "N/A")
            try:
                price_str = f"${float(price):.2f}"
            except:
                price_str = str(price)
            rating = p.get("rating")
            stars = f"{'★' * int(rating)}{'☆' * (5 - int(rating))}" if rating else ""
            link = p.get("link") or p.get("product_link")
            response += (
                f"{i}. **{title}**\n"
                f"💰 Price: {price_str}\n"
                f"{'⭐ ' + stars if stars else ''}\n"
                f"[Buy Now]({link})\n"
                f"_Add to cart: `add to cart {i}`_\n\n"
            )
        return response.strip(), state

    prompt = (
        "You are a friendly Walmart assistant. "
        "Keep replies under 3 sentences and use emojis."
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_message}
    ]
    
    completion = client.chat.completions.create(
        model="openai/gpt-4o",
        messages=messages,
        max_tokens=256,
        temperature=0.6
    )
    
    return completion.choices[0].message.content, state