# Import required libraries
import PySimpleGUI as sg
import csv
import requests
import time

# Define API keys for different chains. Replace with your actual API keys.
API_KEYS = {
    'Ethereum': 'YOUR API KEY',
    'Avalanche': 'YOUR API KEY',
    'BASE': 'YOUR API KEY',
    'Optimism': 'YOUR API KEY',
    'Arbitrum': 'YOUR API KEY',
}

# Define API URLs for different chains.
API_URLS = {
    'Ethereum': 'https://api.etherscan.io/api',
    'Avalanche': 'https://api.snowtrace.io/api',
    'BASE': 'https://api.basescan.org/api', 
    'Optimism': 'https://api-optimistic.etherscan.io/api',
    'Arbitrum': 'https://api.arbiscan.io/api',
}

# Function to fetch transactions for a given blockchain chain and address
def fetch_transactions(chain, address):
    api_key = API_KEYS[chain]
    api_url = API_URLS[chain]
    url = f'{api_url}?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&sort=asc&apikey={api_key}'
    response = requests.get(url)
    data = response.json()
    return data['result'] if data['status'] == '1' else []

# Function to fetch internal transactions
def fetch_internal_transactions(chain, address):
    api_key = API_KEYS[chain]
    api_url = API_URLS[chain]
    url = f'{api_url}?module=account&action=txlistinternal&address={address}&startblock=0&endblock=99999999&sort=asc&apikey={api_key}'
    response = requests.get(url)
    data = response.json()
    return data['result'] if data['status'] == '1' else []

# Function to fetch token transfers
def fetch_token_transfers(chain, address):
    api_key = API_KEYS[chain]
    api_url = API_URLS[chain]
    url = f'{api_url}?module=account&action=tokentx&address={address}&startblock=0&endblock=99999999&sort=asc&apikey={api_key}'
    response = requests.get(url)
    data = response.json()
    return data['result'] if data['status'] == '1' else []

# Function to fetch balances for a given blockchain chain and address
def fetch_balances(chain, address):
    # Get the API key and URL for the specified chain
    api_key = API_KEYS[chain]
    api_url = API_URLS[chain]
    balances = []  # List to store balance data

    # Fetch the native coin balance
    url = f'{api_url}?module=account&action=balance&address={address}&tag=latest&apikey={api_key}'
    response = requests.get(url)
    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError:
        print(f'Failed to decode JSON for native coin balance: {response.text}')
        return balances

    if data['status'] == '1':
        # Calculate the balance and add to the list
        coin_balance = int(data['result']) / 10 ** 18
        balances.append([address, chain, chain, coin_balance])

    # Fetch token balances
    url = f'{api_url}?module=account&action=tokentx&address={address}&startblock=0&endblock=99999999&sort=asc&apikey={api_key}'
    response = requests.get(url)
    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError:
        print(f'Failed to decode JSON for token balances: {response.text}')
        return balances

    if data['status'] == '1':
        seen_tokens = set()  # Track tokens that we've already seen
        for tx in data['result']:
            token_name = tx.get('tokenName', 'Unknown')
            token_symbol = tx.get('tokenSymbol', 'Unknown')
            decimals = int(tx.get('tokenDecimal', 0))
            contract_address = tx['contractAddress']

            if contract_address not in seen_tokens:
                seen_tokens.add(contract_address)
                url = f'{api_url}?module=account&action=tokenbalance&contractaddress={contract_address}&address={address}&tag=latest&apikey={api_key}'
                response = requests.get(url)
                try:
                    token_data = response.json()
                except requests.exceptions.JSONDecodeError:
                    print(f'Failed to decode JSON for specific token balance: {response.text}')
                    continue

                if token_data['status'] == '1':
                    token_balance = int(token_data['result']) / 10 ** decimals
                    balances.append([address, chain, token_name, token_balance])

    # Fetch NFT balances (assuming ERC-721)
    url = f'{api_url}?module=account&action=tokennfttx&address={address}&startblock=0&endblock=99999999&sort=asc&apikey={api_key}'
    response = requests.get(url)
    try:
        nft_data = response.json()
    except requests.exceptions.JSONDecodeError:
        print(f'Failed to decode JSON for NFT data: {response.text}')
        return balances

    if nft_data['status'] == '1':
        seen_nfts = set()
        for tx in nft_data['result']:
            contract_address = tx['contractAddress']
            token_name = tx.get('tokenName', 'Unknown')
            token_id = tx['tokenID']

            if contract_address not in seen_nfts:
                seen_nfts.add(contract_address)
                balances.append([address, chain, f'NFT: {token_name}', token_id])

    time.sleep(1)  # Delay to avoid hitting rate limits
    return balances

# GUI layout
layout = [
    [sg.Text('Enter Wallet Addresses (one per line):')],
    [sg.Multiline(size=(60, 10), key='-WALLETS-')],
    [sg.Text('Select Chain:'), sg.Combo(['Ethereum', 'Avalanche', 'BASE', 'Optimism', 'Arbitrum'], default_value='Ethereum', key='-CHAIN-')],
    [sg.Button('Fetch Balances'), sg.Button('Fetch Transactions'), sg.Button('Exit')]
]

# Create the window
window = sg.Window('Multi-Chain Wallet Checker', layout)

# Event loop
while True:
    event, values = window.read()
    if event == sg.WINDOW_CLOSED or event == 'Exit':
        break

    if event == 'Fetch Balances':
        addresses = values['-WALLETS-'].strip().split('\n')
        selected_chain = values['-CHAIN-']
        all_balances = []

        # Fetch balances for each address
        for address in addresses:
            all_balances.extend(fetch_balances(selected_chain, address))
        
        # Writing the fetched balances to a CSV file
        with open('wallet_balances.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['wallet', 'chain', 'token', 'amount'])
            for row in all_balances:
                writer.writerow(row)

        sg.popup('Done', 'Balances have been written to wallet_balances.csv')

    if event == 'Fetch Transactions':
        addresses = values['-WALLETS-'].strip().split('\n')
        selected_chain = values['-CHAIN-']

        with open('transaction_report.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            # Add 'wallet' to the header row
            writer.writerow(['wallet', 'timestamp', 'hash', 'from', 'to', 'value', 'contractAddress', 'tokenName', 'tokenSymbol', 'amount'])  # Add more fields as needed
            
            # Fetch transactions for each address
            for address in addresses:
                all_transactions = []
                
                transactions = fetch_transactions(selected_chain, address)
                internal_transactions = fetch_internal_transactions(selected_chain, address)
                token_transfers = fetch_token_transfers(selected_chain, address)
                
                # Merge all types of transactions
                all_transactions.extend(transactions)
                all_transactions.extend(internal_transactions)
                all_transactions.extend(token_transfers)

                # Write transactions to the CSV file
                for tx in all_transactions:
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(tx.get('timeStamp'))))
                    # Determine the amount
                    if tx.get('input', '0x')[:10] == '0xa9059cbb':  # This is the method ID for `transfer(address,uint256)` in ERC20
                        amount = int(tx.get('input')[74:], 16) / 10 ** int(tx.get('tokenDecimal', 18))  # Decode the amount from the input data
                    else:
                        amount = int(tx.get('value')) / 10 ** 18  # Convert from wei to ether

                    # Add 'address' to the row
                    writer.writerow([address, timestamp, tx.get('hash'), tx.get('from'), tx.get('to'), tx.get('value'), tx.get('contractAddress'), tx.get('tokenName'), tx.get('tokenSymbol'), amount])

        sg.popup('Done', 'Transactions have been written to transaction_report.csv')

window.close()
