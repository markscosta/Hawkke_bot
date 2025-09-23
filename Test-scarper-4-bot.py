import asyncio
import json
import re
import time
import os
import random
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

class GitHubRubinOTScraper:
    def __init__(self):
        self.deaths_data = []
        self.online_players = []
        self.previous_levels = {}
        self.session = None
        
    def setup_session(self):
        """Setup requests session with retry logic and browser-like headers"""
        self.session = requests.Session()
        
        # Set realistic headers to appear more like a real browser
        self.session.headers.update({
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        })
        
        # Setup retry strategy for network issues
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504, 520, 522, 524],
            allowed_methods=["HEAD", "GET", "POST", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    async def scrape_mystian_data(self):
        """Scrape both deaths and online players from RubinOT Mystian world"""
        try:
            print("Starting GitHub Actions scraper...")
            self.setup_session()
            
            # Check GitHub Actions environment
            if os.getenv('GITHUB_ACTIONS'):
                print("Running in GitHub Actions environment")
            
            # Scrape deaths first
            print("Scraping deaths...")
            deaths = await self.scrape_deaths()
            
            # Wait between requests to be respectful
            await asyncio.sleep(random.uniform(3, 7))
            
            # Scrape online players
            print("Scraping online players...")
            players, level_ups = await self.scrape_online_players()
            
            return {
                'deaths': deaths,
                'online_players': players,
                'level_ups': level_ups
            }
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            return {'deaths': [], 'online_players': [], 'level_ups': []}
        finally:
            if self.session:
                self.session.close()
    
    async def scrape_deaths(self):
        """Scrape deaths from RubinOT Mystian world"""
        try:
            # Random delay to avoid appearing automated
            await asyncio.sleep(random.uniform(2, 4))
            
            print("Fetching deaths page...")
            response = self.session.get('https://rubinot.com.br/?subtopic=latestdeaths', 
                                      timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for world selection form
            world_select = soup.find('select', {'name': 'world'})
            if world_select:
                print("Found world selection, submitting form...")
                
                # Find the form
                form = world_select.find_parent('form')
                if form:
                    # Get form action
                    action = form.get('action', '?subtopic=latestdeaths')
                    if not action.startswith('http'):
                        form_url = f"https://rubinot.com.br/{action.lstrip('/')}"
                    else:
                        form_url = action
                    
                    # Prepare form data
                    form_data = {'world': 'Mystian'}
                    
                    # Add any hidden inputs
                    hidden_inputs = form.find_all('input', type='hidden')
                    for hidden in hidden_inputs:
                        name = hidden.get('name')
                        value = hidden.get('value', '')
                        if name:
                            form_data[name] = value
                    
                    # Wait before submitting
                    await asyncio.sleep(random.uniform(1, 3))
                    
                    # Submit form
                    response = self.session.post(form_url, data=form_data, timeout=30)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')
                    print("Form submitted successfully")
            
            deaths = self.parse_deaths_html(soup)
            print(f"Found {len(deaths)} deaths")
            return deaths
            
        except Exception as e:
            print(f"Error scraping deaths: {e}")
            return []
    
    async def scrape_online_players(self):
        """Scrape online players and detect level changes"""
        try:
            # Random delay between requests
            await asyncio.sleep(random.uniform(2, 4))
            
            print("Fetching online players page...")
            response = self.session.get('https://rubinot.com.br/?subtopic=worlds&world=Mystian', 
                                      timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            players = []
            level_ups = []
            
            # Find the players table - look for table with player data
            tables = soup.find_all('table')
            players_table = None
            
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > 1:
                    # Check if this looks like a players table
                    first_row = rows[1] if len(rows) > 1 else rows[0]
                    cells = first_row.find_all(['td', 'th'])
                    
                    if len(cells) >= 3:
                        # Check if the second cell contains a number (level)
                        try:
                            int(cells[1].get_text().strip())
                            players_table = table
                            break
                        except:
                            continue
            
            if not players_table:
                print("Could not find players table")
                return [], []
            
            # Parse players from the table
            rows = players_table.find_all('tr')[1:]  # Skip header
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:
                    player_name = cells[0].get_text().strip()
                    level_text = cells[1].get_text().strip()
                    vocation = cells[2].get_text().strip() if len(cells) > 2 else 'Unknown'
                    
                    try:
                        current_level = int(level_text)
                        
                        if player_name and current_level > 0:
                            player_data = {
                                'name': player_name,
                                'level': current_level,
                                'vocation': vocation,
                                'timestamp': int(time.time() * 1000)
                            }
                            players.append(player_data)
                            
                            # Check for level changes
                            if player_name in self.previous_levels:
                                previous_level = self.previous_levels[player_name]
                                if current_level > previous_level:
                                    level_difference = current_level - previous_level
                                    level_up = {
                                        'player': player_name,
                                        'previous_level': previous_level,
                                        'new_level': current_level,
                                        'level_gain': level_difference,
                                        'vocation': vocation,
                                        'timestamp': int(time.time() * 1000),
                                        'id': f"{player_name}-{previous_level}-{current_level}-{int(time.time())}"
                                    }
                                    level_ups.append(level_up)
                                    print(f"Level up detected: {player_name} {previous_level} -> {current_level} (+{level_difference})")
                            
                            # Update previous level
                            self.previous_levels[player_name] = current_level
                            
                    except ValueError:
                        continue
            
            print(f"Found {len(players)} online players, {len(level_ups)} level ups")
            return players, level_ups
            
        except Exception as e:
            print(f"Error scraping online players: {e}")
            return [], []
    
    def parse_deaths_html(self, soup):
        """Parse deaths from HTML content"""
        deaths = []
        
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            
            deaths_in_this_table = 0
            for row in rows:
                cells = row.find_all(['td', 'th'])
                
                if len(cells) >= 3:
                    # Look for death information in different cell positions
                    for i in range(len(cells)):
                        cell_text = cells[i].get_text().strip()
                        
                        # Try to match death pattern
                        death_pattern = r'(.+?)\s+died\s+at\s+level\s+(\d+)\s+by\s+(.+?)\.?\s*import asyncio
import json
import re
import time
import os
import random
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import subprocess
import sys

class TorRubinOTScraper:
    def __init__(self):
        self.deaths_data = []
        self.online_players = []
        self.previous_levels = {}
        self.session = None
        self.tor_process = None
        
    def start_tor(self):
        """Start Tor service if not already running"""
        try:
            # Check if Tor is already running
            response = requests.get('http://httpbin.org/ip', 
                                  proxies={'http': 'socks5h://127.0.0.1:9050',
                                          'https': 'socks5h://127.0.0.1:9050'},
                                  timeout=10)
            print("Tor is already running")
            return True
        except:
            try:
                print("Starting Tor service...")
                # Try to start Tor (Linux/Mac)
                self.tor_process = subprocess.Popen(['tor'], 
                                                  stdout=subprocess.DEVNULL, 
                                                  stderr=subprocess.DEVNULL)
                
                # Wait for Tor to initialize
                time.sleep(10)
                
                # Test connection again
                response = requests.get('http://httpbin.org/ip', 
                                      proxies={'http': 'socks5h://127.0.0.1:9050',
                                              'https': 'socks5h://127.0.0.1:9050'},
                                      timeout=10)
                print(f"Tor started successfully. IP: {response.json()['origin']}")
                return True
                
            except Exception as e:
                print(f"Failed to start Tor: {e}")
                return False
    
    def setup_session(self):
        """Setup requests session with Tor proxy and retry logic"""
        self.session = requests.Session()
        
        # Configure Tor proxy
        self.session.proxies = {
            'http': 'socks5h://127.0.0.1:9050',
            'https': 'socks5h://127.0.0.1:9050'
        }
        
        # Set headers to appear more like a real browser
        self.session.headers.update({
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            ]),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Setup retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def get_new_tor_identity(self):
        """Request new Tor circuit for different IP"""
        try:
            # Send NEWNYM signal to Tor control port
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', 9051))
            s.send('AUTHENTICATE ""\r\nSIGNAL NEWNYM\r\nQUIT\r\n'.encode())
            s.close()
            
            # Wait for new circuit
            time.sleep(5)
            print("Requested new Tor identity")
            
        except Exception as e:
            print(f"Could not get new Tor identity: {e}")
    
    async def scrape_mystian_data(self):
        """Scrape both deaths and online players from RubinOT Mystian world"""
        try:
            print("Starting Tor-enabled scraper...")
            
            # Start Tor if needed
            if not self.start_tor():
                print("Failed to start Tor, using direct connection")
                self.session = requests.Session()
            else:
                self.setup_session()
            
            # Test current IP
            try:
                ip_response = self.session.get('http://httpbin.org/ip', timeout=10)
                print(f"Current IP: {ip_response.json()['origin']}")
            except:
                print("Could not determine current IP")
            
            # Scrape deaths first
            print("Scraping deaths...")
            deaths = await self.scrape_deaths()
            
            # Get new Tor identity between requests
            if hasattr(self, 'session') and self.session.proxies:
                self.get_new_tor_identity()
            
            # Scrape online players
            print("Scraping online players...")
            players, level_ups = await self.scrape_online_players()
            
            return {
                'deaths': deaths,
                'online_players': players,
                'level_ups': level_ups
            }
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            return {'deaths': [], 'online_players': [], 'level_ups': []}
        finally:
            if self.session:
                self.session.close()
            if self.tor_process:
                self.tor_process.terminate()
    
    async def scrape_deaths(self):
        """Scrape deaths from RubinOT Mystian world using requests"""
        try:
            # Random delay to avoid detection
            await asyncio.sleep(random.uniform(2, 5))
            
            # Get the deaths page
            response = self.session.get('https://rubinot.com.br/?subtopic=latestdeaths', 
                                      timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find and submit world selection form
            world_form = soup.find('form')
            if world_form:
                # Submit form with Mystian world selection
                form_data = {'world': 'Mystian'}
                
                # Find form action
                action = world_form.get('action', '')
                if action:
                    form_url = f"https://rubinot.com.br/{action}" if not action.startswith('http') else action
                else:
                    form_url = 'https://rubinot.com.br/?subtopic=latestdeaths'
                
                # Wait before submitting form
                await asyncio.sleep(random.uniform(1, 3))
                
                response = self.session.post(form_url, data=form_data, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
            
            deaths = self.parse_deaths_html(soup)
            return deaths
            
        except Exception as e:
            print(f"Error scraping deaths: {e}")
            return []
    
    async def scrape_online_players(self):
        """Scrape online players and detect level changes using requests"""
        try:
            # Random delay between requests
            await asyncio.sleep(random.uniform(2, 5))
            
            response = self.session.get('https://rubinot.com.br/?subtopic=worlds&world=Mystian', 
                                      timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            players = []
            level_ups = []
            
            # Find the players table
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > 1:  # Has header + data
                    for i, row in enumerate(rows[1:], 1):  # Skip header
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 3:
                            player_name = cells[0].get_text().strip()
                            level_text = cells[1].get_text().strip()
                            vocation = cells[2].get_text().strip() if len(cells) > 2 else 'Unknown'
                            
                            try:
                                current_level = int(level_text)
                                
                                if player_name and current_level > 0:
                                    player_data = {
                                        'name': player_name,
                                        'level': current_level,
                                        'vocation': vocation,
                                        'timestamp': int(time.time() * 1000)
                                    }
                                    players.append(player_data)
                                    
                                    # Check for level changes
                                    if player_name in self.previous_levels:
                                        previous_level = self.previous_levels[player_name]
                                        if current_level > previous_level:
                                            level_difference = current_level - previous_level
                                            level_up = {
                                                'player': player_name,
                                                'previous_level': previous_level,
                                                'new_level': current_level,
                                                'level_gain': level_difference,
                                                'vocation': vocation,
                                                'timestamp': int(time.time() * 1000),
                                                'id': f"{player_name}-{previous_level}-{current_level}-{int(time.time())}"
                                            }
                                            level_ups.append(level_up)
                                            print(f"Level up detected: {player_name} {previous_level} -> {current_level} (+{level_difference})")
                                    
                                    # Update previous level
                                    self.previous_levels[player_name] = current_level
                                    
                            except ValueError:
                                continue
                    
                    if players:  # Found valid players table
                        break
            
            print(f"Found {len(players)} online players, {len(level_ups)} level ups")
            return players, level_ups
            
        except Exception as e:
            print(f"Error scraping online players: {e}")
            return [], []
    
    def parse_deaths_html(self, soup):
        """Parse deaths from HTML content"""
        deaths = []
        
        tables = soup.find_all('table')
        for table_idx, table in enumerate(tables):
            rows = table.find_all('tr')
            
            deaths_in_this_table = 0
            for i, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                
                if len(cells) >= 3:
                    death_text = cells[2].get_text().strip()
                    time_text = cells[1].get_text().strip()
                    
                    death_pattern = r'(.+?)\s+died\s+at\s+level\s+(\d+)\s+by\s+(.+?)\.?\s*$'
                    match = re.search(death_pattern, death_text, re.IGNORECASE)
                    
                    if match:
                        player = match.group(1).strip()
                        level = int(match.group(2))
                        killer = match.group(3).strip()
                        
                        if killer.endswith('.'):
                            killer = killer[:-1]
                        
                        death_data = {
                            'player': player,
                            'level': level,
                            'killer': killer,
                            'time': time_text,
                            'timestamp': int(time.time() * 1000),
                            'id': f"{player}-{level}-{killer}-{time_text}"
                        }
                        deaths.append(death_data)
                        deaths_in_this_table += 1
                        
                        if deaths_in_this_table <= 3:  # Only print first few
                            print(f"Parsed death: {player} (lvl {level}) killed by {killer}")
            
            if deaths_in_this_table > 0:
                break
        
        return deaths[:20]  # Return max 20 recent deaths
    
    def load_previous_levels(self):
        """Load previous level data from file"""
        try:
            if os.path.exists('previous_levels.json'):
                with open('previous_levels.json', 'r') as f:
                    self.previous_levels = json.load(f)
                    print(f"Loaded {len(self.previous_levels)} previous player levels")
            else:
                print("No previous levels file found, starting fresh")
                self.previous_levels = {}
        except Exception as e:
            print(f"Error loading previous levels: {e}")
            self.previous_levels = {}
    
    def save_previous_levels(self):
        """Save current level data for next run"""
        try:
            with open('previous_levels.json', 'w') as f:
                json.dump(self.previous_levels, f, indent=2)
        except Exception as e:
            print(f"Error saving previous levels: {e}")
    
    def save_data(self, data):
        """Save all scraped data to JSON files"""
        try:
            # Save deaths
            deaths_data = {
                'lastUpdated': datetime.now().isoformat(),
                'world': 'Mystian',
                'data': data['deaths']
            }
            with open('rubinot_deaths.json', 'w') as f:
                json.dump(deaths_data, f, indent=2)
            
            # Save online players
            players_data = {
                'lastUpdated': datetime.now().isoformat(),
                'world': 'Mystian',
                'data': data['online_players']
            }
            with open('rubinot_players.json', 'w') as f:
                json.dump(players_data, f, indent=2)
            
            # Save level ups
            levelups_data = {
                'lastUpdated': datetime.now().isoformat(),
                'world': 'Mystian',
                'data': data['level_ups']
            }
            with open('rubinot_levelups.json', 'w') as f:
                json.dump(levelups_data, f, indent=2)
            
            print(f"Saved {len(data['deaths'])} deaths, {len(data['online_players'])} players, {len(data['level_ups'])} level ups")
            
        except Exception as e:
            print(f"Error saving data: {e}")

async def main():
    scraper = TorRubinOTScraper()
    
    print("Starting RubinOT Tor-enabled scraper...")
    
    # Load previous level data
    scraper.load_previous_levels()
    
    # Scrape all data
    data = await scraper.scrape_mystian_data()
    
    # Save results
    if data['deaths'] or data['online_players'] or data['level_ups']:
        scraper.save_data(data)
        scraper.save_previous_levels()
        
        print(f"\nScraping complete!")
        print(f"Results:")
        print(f"   Deaths: {len(data['deaths'])}")
        print(f"   Online Players: {len(data['online_players'])}")
        print(f"   Level Ups: {len(data['level_ups'])}")
        
        if data['level_ups']:
            print(f"\nRecent Level Ups:")
            for levelup in data['level_ups'][:5]:
                print(f"   {levelup['player']}: {levelup['previous_level']} -> {levelup['new_level']} (+{levelup['level_gain']})")
    else:
        print("No data found")
    
    print("\nScraper complete!")

if __name__ == "__main__":
    asyncio.run(main())
                        match = re.search(death_pattern, cell_text, re.IGNORECASE)
                        
                        if match:
                            player = match.group(1).strip()
                            level = int(match.group(2))
                            killer = match.group(3).strip()
                            
                            if killer.endswith('.'):
                                killer = killer[:-1]
                            
                            # Try to get time from another cell
                            time_text = "Unknown"
                            if i > 0:
                                time_text = cells[i-1].get_text().strip()
                            elif i < len(cells) - 1:
                                time_text = cells[i+1].get_text().strip()
                            
                            death_data = {
                                'player': player,
                                'level': level,
                                'killer': killer,
                                'time': time_text,
                                'timestamp': int(time.time() * 1000),
                                'id': f"{player}-{level}-{killer}-{int(time.time())}"
                            }
                            
                            # Check for duplicates
                            if not any(d['player'] == player and d['level'] == level and d['killer'] == killer for d in deaths):
                                deaths.append(death_data)
                                deaths_in_this_table += 1
                                print(f"Parsed death: {player} (lvl {level}) killed by {killer}")
                            
                            break
            
            if deaths_in_this_table > 0:
                break
        
        return deaths[:20]  # Return max 20 recent deaths
    
    def load_previous_levels(self):
        """Load previous level data from file"""
        try:
            if os.path.exists('previous_levels.json'):
                with open('previous_levels.json', 'r', encoding='utf-8') as f:
                    self.previous_levels = json.load(f)
                    print(f"Loaded {len(self.previous_levels)} previous player levels")
            else:
                print("No previous levels file found, starting fresh")
                self.previous_levels = {}
        except Exception as e:
            print(f"Error loading previous levels: {e}")
            self.previous_levels = {}
    
    def save_previous_levels(self):
        """Save current level data for next run"""
        try:
            with open('previous_levels.json', 'w', encoding='utf-8') as f:
                json.dump(self.previous_levels, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving previous levels: {e}")
    
    def save_data(self, data):
        """Save all scraped data to JSON files"""
        try:
            timestamp = datetime.now().isoformat()
            
            # Save deaths
            deaths_data = {
                'lastUpdated': timestamp,
                'world': 'Mystian',
                'scraper': 'GitHub Actions',
                'data': data['deaths']
            }
            with open('rubinot_deaths.json', 'w', encoding='utf-8') as f:
                json.dump(deaths_data, f, indent=2, ensure_ascii=False)
            
            # Save online players
            players_data = {
                'lastUpdated': timestamp,
                'world': 'Mystian', 
                'scraper': 'GitHub Actions',
                'data': data['online_players']
            }
            with open('rubinot_players.json', 'w', encoding='utf-8') as f:
                json.dump(players_data, f, indent=2, ensure_ascii=False)
            
            # Save level ups
            levelups_data = {
                'lastUpdated': timestamp,
                'world': 'Mystian',
                'scraper': 'GitHub Actions', 
                'data': data['level_ups']
            }
            with open('rubinot_levelups.json', 'w', encoding='utf-8') as f:
                json.dump(levelups_data, f, indent=2, ensure_ascii=False)
            
            print(f"Saved {len(data['deaths'])} deaths, {len(data['online_players'])} players, {len(data['level_ups'])} level ups")
            
        except Exception as e:
            print(f"Error saving data: {e}")

async def main():
    scraper = GitHubRubinOTScraper()
    
    print("Starting RubinOT GitHub Actions scraper...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Load previous level data
    scraper.load_previous_levels()
    
    # Scrape all data
    data = await scraper.scrape_mystian_data()
    
    # Save results
    if data['deaths'] or data['online_players'] or data['level_ups']:
        scraper.save_data(data)
        scraper.save_previous_levels()
        
        print(f"\nScraping complete!")
        print(f"Results:")
        print(f"   Deaths: {len(data['deaths'])}")
        print(f"   Online Players: {len(data['online_players'])}")
        print(f"   Level Ups: {len(data['level_ups'])}")
        
        if data['level_ups']:
            print(f"\nRecent Level Ups:")
            for levelup in data['level_ups'][:5]:
                print(f"   {levelup['player']}: {levelup['previous_level']} -> {levelup['new_level']} (+{levelup['level_gain']})")
    else:
        print("No data found")
    
    print("\nScraper complete!")

if __name__ == "__main__":
    asyncio.run(main())import asyncio
import json
import re
import time
import os
import random
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import subprocess
import sys

class TorRubinOTScraper:
    def __init__(self):
        self.deaths_data = []
        self.online_players = []
        self.previous_levels = {}
        self.session = None
        self.tor_process = None
        
    def start_tor(self):
        """Start Tor service if not already running"""
        try:
            # Check if Tor is already running
            response = requests.get('http://httpbin.org/ip', 
                                  proxies={'http': 'socks5h://127.0.0.1:9050',
                                          'https': 'socks5h://127.0.0.1:9050'},
                                  timeout=10)
            print("Tor is already running")
            return True
        except:
            try:
                print("Starting Tor service...")
                # Try to start Tor (Linux/Mac)
                self.tor_process = subprocess.Popen(['tor'], 
                                                  stdout=subprocess.DEVNULL, 
                                                  stderr=subprocess.DEVNULL)
                
                # Wait for Tor to initialize
                time.sleep(10)
                
                # Test connection again
                response = requests.get('http://httpbin.org/ip', 
                                      proxies={'http': 'socks5h://127.0.0.1:9050',
                                              'https': 'socks5h://127.0.0.1:9050'},
                                      timeout=10)
                print(f"Tor started successfully. IP: {response.json()['origin']}")
                return True
                
            except Exception as e:
                print(f"Failed to start Tor: {e}")
                return False
    
    def setup_session(self):
        """Setup requests session with Tor proxy and retry logic"""
        self.session = requests.Session()
        
        # Configure Tor proxy
        self.session.proxies = {
            'http': 'socks5h://127.0.0.1:9050',
            'https': 'socks5h://127.0.0.1:9050'
        }
        
        # Set headers to appear more like a real browser
        self.session.headers.update({
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            ]),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Setup retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def get_new_tor_identity(self):
        """Request new Tor circuit for different IP"""
        try:
            # Send NEWNYM signal to Tor control port
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', 9051))
            s.send('AUTHENTICATE ""\r\nSIGNAL NEWNYM\r\nQUIT\r\n'.encode())
            s.close()
            
            # Wait for new circuit
            time.sleep(5)
            print("Requested new Tor identity")
            
        except Exception as e:
            print(f"Could not get new Tor identity: {e}")
    
    async def scrape_mystian_data(self):
        """Scrape both deaths and online players from RubinOT Mystian world"""
        try:
            print("Starting Tor-enabled scraper...")
            
            # Start Tor if needed
            if not self.start_tor():
                print("Failed to start Tor, using direct connection")
                self.session = requests.Session()
            else:
                self.setup_session()
            
            # Test current IP
            try:
                ip_response = self.session.get('http://httpbin.org/ip', timeout=10)
                print(f"Current IP: {ip_response.json()['origin']}")
            except:
                print("Could not determine current IP")
            
            # Scrape deaths first
            print("Scraping deaths...")
            deaths = await self.scrape_deaths()
            
            # Get new Tor identity between requests
            if hasattr(self, 'session') and self.session.proxies:
                self.get_new_tor_identity()
            
            # Scrape online players
            print("Scraping online players...")
            players, level_ups = await self.scrape_online_players()
            
            return {
                'deaths': deaths,
                'online_players': players,
                'level_ups': level_ups
            }
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            return {'deaths': [], 'online_players': [], 'level_ups': []}
        finally:
            if self.session:
                self.session.close()
            if self.tor_process:
                self.tor_process.terminate()
    
    async def scrape_deaths(self):
        """Scrape deaths from RubinOT Mystian world using requests"""
        try:
            # Random delay to avoid detection
            await asyncio.sleep(random.uniform(2, 5))
            
            # Get the deaths page
            response = self.session.get('https://rubinot.com.br/?subtopic=latestdeaths', 
                                      timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find and submit world selection form
            world_form = soup.find('form')
            if world_form:
                # Submit form with Mystian world selection
                form_data = {'world': 'Mystian'}
                
                # Find form action
                action = world_form.get('action', '')
                if action:
                    form_url = f"https://rubinot.com.br/{action}" if not action.startswith('http') else action
                else:
                    form_url = 'https://rubinot.com.br/?subtopic=latestdeaths'
                
                # Wait before submitting form
                await asyncio.sleep(random.uniform(1, 3))
                
                response = self.session.post(form_url, data=form_data, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
            
            deaths = self.parse_deaths_html(soup)
            return deaths
            
        except Exception as e:
            print(f"Error scraping deaths: {e}")
            return []
    
    async def scrape_online_players(self):
        """Scrape online players and detect level changes using requests"""
        try:
            # Random delay between requests
            await asyncio.sleep(random.uniform(2, 5))
            
            response = self.session.get('https://rubinot.com.br/?subtopic=worlds&world=Mystian', 
                                      timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            players = []
            level_ups = []
            
            # Find the players table
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > 1:  # Has header + data
                    for i, row in enumerate(rows[1:], 1):  # Skip header
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 3:
                            player_name = cells[0].get_text().strip()
                            level_text = cells[1].get_text().strip()
                            vocation = cells[2].get_text().strip() if len(cells) > 2 else 'Unknown'
                            
                            try:
                                current_level = int(level_text)
                                
                                if player_name and current_level > 0:
                                    player_data = {
                                        'name': player_name,
                                        'level': current_level,
                                        'vocation': vocation,
                                        'timestamp': int(time.time() * 1000)
                                    }
                                    players.append(player_data)
                                    
                                    # Check for level changes
                                    if player_name in self.previous_levels:
                                        previous_level = self.previous_levels[player_name]
                                        if current_level > previous_level:
                                            level_difference = current_level - previous_level
                                            level_up = {
                                                'player': player_name,
                                                'previous_level': previous_level,
                                                'new_level': current_level,
                                                'level_gain': level_difference,
                                                'vocation': vocation,
                                                'timestamp': int(time.time() * 1000),
                                                'id': f"{player_name}-{previous_level}-{current_level}-{int(time.time())}"
                                            }
                                            level_ups.append(level_up)
                                            print(f"Level up detected: {player_name} {previous_level} -> {current_level} (+{level_difference})")
                                    
                                    # Update previous level
                                    self.previous_levels[player_name] = current_level
                                    
                            except ValueError:
                                continue
                    
                    if players:  # Found valid players table
                        break
            
            print(f"Found {len(players)} online players, {len(level_ups)} level ups")
            return players, level_ups
            
        except Exception as e:
            print(f"Error scraping online players: {e}")
            return [], []
    
    def parse_deaths_html(self, soup):
        """Parse deaths from HTML content"""
        deaths = []
        
        tables = soup.find_all('table')
        for table_idx, table in enumerate(tables):
            rows = table.find_all('tr')
            
            deaths_in_this_table = 0
            for i, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                
                if len(cells) >= 3:
                    death_text = cells[2].get_text().strip()
                    time_text = cells[1].get_text().strip()
                    
                    death_pattern = r'(.+?)\s+died\s+at\s+level\s+(\d+)\s+by\s+(.+?)\.?\s*$'
                    match = re.search(death_pattern, death_text, re.IGNORECASE)
                    
                    if match:
                        player = match.group(1).strip()
                        level = int(match.group(2))
                        killer = match.group(3).strip()
                        
                        if killer.endswith('.'):
                            killer = killer[:-1]
                        
                        death_data = {
                            'player': player,
                            'level': level,
                            'killer': killer,
                            'time': time_text,
                            'timestamp': int(time.time() * 1000),
                            'id': f"{player}-{level}-{killer}-{time_text}"
                        }
                        deaths.append(death_data)
                        deaths_in_this_table += 1
                        
                        if deaths_in_this_table <= 3:  # Only print first few
                            print(f"Parsed death: {player} (lvl {level}) killed by {killer}")
            
            if deaths_in_this_table > 0:
                break
        
        return deaths[:20]  # Return max 20 recent deaths
    
    def load_previous_levels(self):
        """Load previous level data from file"""
        try:
            if os.path.exists('previous_levels.json'):
                with open('previous_levels.json', 'r') as f:
                    self.previous_levels = json.load(f)
                    print(f"Loaded {len(self.previous_levels)} previous player levels")
            else:
                print("No previous levels file found, starting fresh")
                self.previous_levels = {}
        except Exception as e:
            print(f"Error loading previous levels: {e}")
            self.previous_levels = {}
    
    def save_previous_levels(self):
        """Save current level data for next run"""
        try:
            with open('previous_levels.json', 'w') as f:
                json.dump(self.previous_levels, f, indent=2)
        except Exception as e:
            print(f"Error saving previous levels: {e}")
    
    def save_data(self, data):
        """Save all scraped data to JSON files"""
        try:
            # Save deaths
            deaths_data = {
                'lastUpdated': datetime.now().isoformat(),
                'world': 'Mystian',
                'data': data['deaths']
            }
            with open('rubinot_deaths.json', 'w') as f:
                json.dump(deaths_data, f, indent=2)
            
            # Save online players
            players_data = {
                'lastUpdated': datetime.now().isoformat(),
                'world': 'Mystian',
                'data': data['online_players']
            }
            with open('rubinot_players.json', 'w') as f:
                json.dump(players_data, f, indent=2)
            
            # Save level ups
            levelups_data = {
                'lastUpdated': datetime.now().isoformat(),
                'world': 'Mystian',
                'data': data['level_ups']
            }
            with open('rubinot_levelups.json', 'w') as f:
                json.dump(levelups_data, f, indent=2)
            
            print(f"Saved {len(data['deaths'])} deaths, {len(data['online_players'])} players, {len(data['level_ups'])} level ups")
            
        except Exception as e:
            print(f"Error saving data: {e}")

async def main():
    scraper = TorRubinOTScraper()
    
    print("Starting RubinOT Tor-enabled scraper...")
    
    # Load previous level data
    scraper.load_previous_levels()
    
    # Scrape all data
    data = await scraper.scrape_mystian_data()
    
    # Save results
    if data['deaths'] or data['online_players'] or data['level_ups']:
        scraper.save_data(data)
        scraper.save_previous_levels()
        
        print(f"\nScraping complete!")
        print(f"Results:")
        print(f"   Deaths: {len(data['deaths'])}")
        print(f"   Online Players: {len(data['online_players'])}")
        print(f"   Level Ups: {len(data['level_ups'])}")
        
        if data['level_ups']:
            print(f"\nRecent Level Ups:")
            for levelup in data['level_ups'][:5]:
                print(f"   {levelup['player']}: {levelup['previous_level']} -> {levelup['new_level']} (+{levelup['level_gain']})")
    else:
        print("No data found")
    
    print("\nScraper complete!")

if __name__ == "__main__":
    asyncio.run(main())
