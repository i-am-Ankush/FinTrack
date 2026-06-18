"""
Rule-based keyword → category mapping.
Used to (a) label transactions directly and (b) generate ML training data.
"""

RULES = {
    'Food':          ['swiggy', 'zomato', 'dominos', 'pizza', 'mess', 'canteen',
                      'restaurant', 'hotel', 'cafe', 'biryani', 'burger', 'food',
                      'eat', 'lunch', 'dinner', 'breakfast', 'dabba'],
    'Transport':     ['ola', 'uber', 'rapido', 'bus', 'train', 'flight', 'petrol',
                      'fuel', 'auto', 'rickshaw', 'metro', 'taxi', 'irctc'],
    'Shopping':      ['amazon', 'flipkart', 'myntra', 'meesho', 'nykaa', 'ajio',
                      'shopping', 'purchase', 'buy', 'store', 'market', 'mall'],
    'Education':     ['coursera', 'udemy', 'books', 'stationery', 'fees', 'library',
                      'tuition', 'course', 'college', 'university', 'exam'],
    'Health':        ['pharmacy', 'hospital', 'doctor', 'medicine', 'clinic',
                      'netmeds', 'apollo', 'health', 'medical', '1mg', 'pharma'],
    'Entertainment': ['netflix', 'spotify', 'prime', 'hotstar', 'pvr', 'inox',
                      'game', 'gaming', 'steam', 'youtube', 'movie', 'show'],
    'Utilities':     ['electricity', 'water', 'wifi', 'phone', 'recharge', 'airtel',
                      'jio', 'bsnl', 'vi', 'vodafone', 'bill', 'postpaid', 'prepaid'],
    'Income':        ['salary', 'stipend', 'cashback', 'refund', 'received',
                      'credited', 'credit', 'transfer in', 'neft in', 'imps in',
                      'upi in', 'interest', 'dividend'],
}

def rule_classify(description: str) -> str:
    """Return category using keyword rules. Falls back to 'Other'."""
    desc = description.lower()
    for category, keywords in RULES.items():
        for kw in keywords:
            if kw in desc:
                return category
    return 'Other'
