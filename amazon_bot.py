from bs4 import BeautifulSoup
from selenium import webdriver as wb
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email import encoders
from email.mime.base import MIMEBase
from email import encoders
import os.path
import smtplib

options = wb.ChromeOptions()
# helps to take full screenshot of the browser and not just the visible window
options.headless = False
WBD = wb.Chrome('/path_to_chromedriver', options=options)


def log_in():
    """Launches a chrome window and logins into the amazon account"""
    signin = open('accounts.txt', 'r').read().split('\n')
    amzuser, amzpass = signin[0].split(":")
    WBD.get('https://www.amazon.com/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.com%2F%3Fref_%3Dnav_ya_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=usflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&')
    WBD.find_element_by_xpath('//*[@id="ap_email"]').send_keys(amzuser)
    WBD.find_element_by_xpath('//*[@id="continue"]').click()
    WBD.find_element_by_xpath('//*[@id="ap_password"]').send_keys(amzpass)
    WBD.find_element_by_xpath('//*[@id="signInSubmit"]').click()
    time.sleep(2)


def get_url(search_item):
    "Generates a url for the products that I want to buy"
    url_template = 'https://www.amazon.com/s?k={}&ref=nb_sb_noss_2'
    search_item = search_item.replace(' ', '+')
    # check multiple pages and products
    # avoiding errors by generating url instead of search each item on the list
    url = url_template.format(search_item)
    # update page number
    url += '&page{}'
    return url


def get_product_info(item):
    """scrape search page to find price, product url, and rating count"""
    atag = item.h2.a
    product_info = atag.text.strip().replace(
        '/', ' ').replace('-', ' ').replace(',', ' ')
    url = 'https://www.amazon.com' + atag.get('href')

    try:
        price_parent = item.find('span', 'a-price')
        price = price_parent.find(
            'span', 'a-offscreen').text.strip('$').replace(',', '')
    except AttributeError:
        return
    try:
        product_image = item.find('img')
        image_link = product_image['src']
    except AttributeError:
        return "No image found"
    try:
        rating_count = item.find(
            'span', {'class': 'a-size-base'}).text.replace(',', '')
    except AttributeError:
        return
    except ValueError:
        return
    except TypeError:
        rating_count = item.find(
            'span', {'class': 'a-size-base'}).text.replace(',', '')
        rating_count = 0
    if (type(rating_count[0] != int)):
        rating_count = 0
    result = {"Product Title": product_info.lower(), "Price": float(price),  "Rating Count": int(
        rating_count), "Product Url": url, "Product Image": image_link}
    return result


def find_matches(records, key_words):
    """Returns the product url for the best product"""
    match_titles = [i for i in records if all(
        w in i['Product Title'] for w in key_words)]  # check that everyword in the buy list is in there and pop it
    # highest rated from qualified products
    item = max(match_titles, key=lambda i: i['Rating Count'])
    return item.get('Product Url')


def add_to_cart(product_url):
    """adds the decided on product to cart"""
    WBD.get(product_url)
    WBD.find_element_by_xpath('//*[@id="add-to-cart-button"]').click()
    WBD.implicitly_wait(5)
    try:  # declines insurnace pop out if it pops up
        WBD.find_element_by_xpath(
            '//*[@id="attachSiNoCoverage"]/span/input').click()
        time.sleep(5)
    except:
        print("No insurnance pop out window found!")


def cart_info():
    """sends a full screenshot of the browser to show all of the items in the email"""
    def S(X): return WBD.execute_script(
        'return document.body.parentNode.scroll'+X)
    WBD.set_window_size(S('Width'), S('Height'))
    WBD.find_element_by_tag_name('body').screenshot('cart_screenshot.png')
    signin = open('accounts.txt', 'r').read().split('\n')
    senderId, senderpass = signin[1].split(":")
    file_location = '/Users/yonas/Desktop/auto/cart_screenshot.png'
    msg = MIMEMultipart()
    msg['From'] = senderId
    msg['To'] = 'email address that you want the cart screenshot to be sent to'
    msg['Subject'] = 'Amazon Cart Info'
    msg.attach(MIMEText(
        'Please review the cart and confirm on the terminal window.', 'plain'))
    filename = os.path.basename(file_location)
    attachment = open(file_location, "rb")
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition',
                    "attachment; filename= %s" % filename)
    msg.attach(part)
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(senderId, senderpass)
    text = msg.as_string()
    server.sendmail(senderId, 'enter same email as before', text)
    server.quit()


def checkout():
    """Checkout procedure"""
    WBD.implicitly_wait(5)
    WBD.find_element_by_xpath(
        '//*[@id="sc-buy-box-ptc-button"]/span/input').click()
    WBD.implicitly_wait(5)
    WBD.find_element_by_xpath(
        '//*[@id="submitOrderButtonId"]/span/input').click()


def main(file_name):
    log_in()
    buy_list = open(file_name, 'r').read().split('\n')
    for ptb in buy_list:  # products to buy
        records = []
        url = get_url(ptb)
        for page in range(1, 2):
            WBD.get(url.format(page))
            soup = BeautifulSoup(WBD.page_source, 'html.parser')
            results = soup.find_all(
                'div', {'data-component-type': 's-search-result'})
            for item in results:
                record = get_product_info(item)
                if record:
                    records.append(record)
        key_words = ptb.split(' ')
        match = find_matches(records, key_words)
        add_to_cart(match)

    WBD.get('https://www.amazon.com/gp/cart/view.html?ref_=nav_cart')
    cart_info()
    confirmation = input(
        "Check the email sent! Do you want to execute that order?")
    if confirmation.lower() == 'yes':
        checkout()
        print("Order Submitted!")
    else:
        print("Please manually search for the products that are incorrectly added to your cart.")

    time.sleep(15)
    WBD.close()


main('buy_list.txt') #enter a text file with each order on a separate lines
