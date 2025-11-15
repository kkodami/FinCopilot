from typing import Dict

def format_report(data: Dict, analysis: str) -> str:
    """Форматирование отчета в читаемый вид"""
    
    if not data:
        return "❌ Не удалось сформировать отчет"
    
    income = data.get('income', 0)
    expenses = data.get('expenses', 0)
    profit = data.get('profit', 0)
    
    report = f"""
📊 **Финансовый отчет**

💵 **Доходы:** {income:,.0f} руб
💸 **Расходы:** {expenses:,.0f} руб
💰 **Прибыль:** {profit:,.0f} руб
📈 **Рентабельность:** {(profit/income*100) if income > 0 else 0:.1f}%

---

{analysis}
"""
    return report

def validate_amount(amount: float) -> bool:
    """Валидация суммы"""
    return amount > 0 and amount < 10**9  # разумные пределы

def format_currency(amount: float, currency: str = "RUB") -> str:
    """Форматирование валюты"""
    return f"{amount:,.0f} {currency}"