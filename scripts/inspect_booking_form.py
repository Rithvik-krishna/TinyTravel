from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=False)
    page = b.new_page()
    page.goto('https://www.booking.com/hotel/in/radisson-blu-atria-bengaluru.html?checkin=2026-11-20&checkout=2026-11-21&group_adults=2&no_rooms=1&selected_currency=INR')
    page.wait_for_timeout(4000)
    info = page.evaluate("""() => {
        const form = document.querySelector('#hprt-form, form[name="book"]');
        const btns = Array.from(document.querySelectorAll('button')).filter(b => b.innerText.includes('reserve') || b.innerText.includes('Reserve'));
        return {
            formAction: form ? form.action : null,
            formMethod: form ? form.method : null,
            buttons: btns.map(b => ({ cls: b.className, type: b.type, text: b.innerText }))
        };
    }""")
    print(info)
    b.close()
