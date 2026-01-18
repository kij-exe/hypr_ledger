#!/usr/bin/env python3
"""
Hyperliquid Deposit Tracker
Retrieves and displays all deposits, withdrawals, and rewards for a user.

Usage:
    python get_deposits.py <user_address> [--days=30] [--include-rewards]

Example:
    python get_deposits.py 0x123... --days=90 --include-rewards
"""

import requests
import sys
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import argparse
from tabulate import tabulate


@dataclass
class LedgerUpdate:
    """Represents a ledger update (deposit, withdrawal, etc.)"""
    time_ms: int
    update_type: str
    category: str
    amount: float
    hash: str
    details: Dict


class HyperliquidDepositTracker:
    """Track deposits and withdrawals for a Hyperliquid user"""
    
    API_URL = "https://api.hyperliquid.xyz/info"
    
    # Categorize update types
    DEPOSIT_TYPES = ['deposit']
    WITHDRAW_TYPES = ['withdraw']
    REWARD_TYPES = ['vaultDistribution', 'referral', 'rewardClaim', 'stakingReward']
    LOSS_TYPES = ['liquidation']
    INTERNAL_TYPES = ['internalTransfer', 'accountClassTransfer', 
                      'subAccountTransfer', 'spotTransfer', 'vaultCreate']
    
    def __init__(self):
        pass
    
    def get_ledger_updates(
        self, 
        user: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[Dict]:
        """
        Get non-funding ledger updates from Hyperliquid API
        
        Args:
            user: User address
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
        
        Returns:
            List of ledger updates
        """
        payload = {
            "type": "userNonFundingLedgerUpdates",
            "user": user,
            "startTime": start_time or 0
        }
        
        if end_time:
            payload["endTime"] = end_time
        
        try:
            response = requests.post(
                self.API_URL,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: API returned status {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Error fetching ledger updates: {e}")
            return []
    
    def categorize_update(self, update_type: str) -> str:
        """Categorize an update type"""
        if update_type in self.DEPOSIT_TYPES:
            return "deposit"
        elif update_type in self.WITHDRAW_TYPES:
            return "withdraw"
        elif update_type in self.REWARD_TYPES:
            return "reward"
        elif update_type in self.LOSS_TYPES:
            return "loss"
        elif update_type in self.INTERNAL_TYPES:
            return "internal"
        else:
            return "other"
    
    def parse_updates(
        self,
        raw_updates: List[Dict]
    ) -> List[LedgerUpdate]:
        """Parse raw API updates into structured format"""
        parsed = []
        
        for update in raw_updates:
            time_ms = update.get('time', 0)
            delta = update.get('delta', {})
            update_type = delta.get('type', 'unknown')
            
            # Get amount (USDC)
            amount = float(delta.get('usdc', 0))
            
            # Categorize
            category = self.categorize_update(update_type)
            
            # Make withdrawals and losses positive for display
            if category in ['withdraw', 'loss']:
                amount = abs(amount)
            
            parsed.append(LedgerUpdate(
                time_ms=time_ms,
                update_type=update_type,
                category=category,
                amount=amount,
                hash=update.get('hash', ''),
                details=delta
            ))
        
        return parsed
    
    def analyze_deposits(
        self,
        user: str,
        days: int = 30,
        include_rewards: bool = False
    ) -> Dict:
        """
        Analyze deposits for a user
        
        Args:
            user: User address
            days: Number of days to look back
            include_rewards: Count rewards as deposits
        
        Returns:
            Analysis dict with deposits, withdrawals, rewards
        """
        # Calculate time range
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        print(f"Fetching ledger updates for {user}...")
        print(f"Period: Last {days} days")
        print(f"From: {datetime.fromtimestamp(start_time/1000).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"To:   {datetime.fromtimestamp(end_time/1000).strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Get raw updates
        raw_updates = self.get_ledger_updates(user, start_time, end_time)
        
        if not raw_updates:
            print("No ledger updates found")
            return None
        
        print(f"Found {len(raw_updates)} ledger updates")
        print()
        
        # Parse updates
        updates = self.parse_updates(raw_updates)
        
        # Categorize
        deposits = [u for u in updates if u.category == 'deposit']
        withdrawals = [u for u in updates if u.category == 'withdraw']
        rewards = [u for u in updates if u.category == 'reward']
        losses = [u for u in updates if u.category == 'loss']
        internals = [u for u in updates if u.category == 'internal']
        others = [u for u in updates if u.category == 'other']
        
        # Calculate totals
        total_deposits = sum(d.amount for d in deposits)
        total_withdrawals = sum(w.amount for w in withdrawals)
        total_rewards = sum(r.amount for r in rewards)
        total_losses = sum(l.amount for l in losses)
        
        # Net change
        net_deposits = total_deposits - total_withdrawals
        net_with_rewards = net_deposits + total_rewards - total_losses
        
        return {
            'user': user,
            'period_days': days,
            'start_time': start_time,
            'end_time': end_time,
            'deposits': deposits,
            'withdrawals': withdrawals,
            'rewards': rewards,
            'losses': losses,
            'internals': internals,
            'others': others,
            'total_deposits': total_deposits,
            'total_withdrawals': total_withdrawals,
            'total_rewards': total_rewards,
            'total_losses': total_losses,
            'net_deposits': net_deposits,
            'net_with_rewards': net_with_rewards,
            'deposit_count': len(deposits),
            'withdrawal_count': len(withdrawals),
            'reward_count': len(rewards),
        }


def format_timestamp(time_ms: int) -> str:
    """Format timestamp for display"""
    dt = datetime.fromtimestamp(time_ms / 1000)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def format_amount(amount: float) -> str:
    """Format amount with color"""
    if amount >= 0:
        return f"+${amount:,.2f}"
    else:
        return f"-${abs(amount):,.2f}"


def print_summary(analysis: Dict):
    """Print summary statistics"""
    print("=" * 80)
    print("DEPOSIT SUMMARY")
    print("=" * 80)
    print(f"User: {analysis['user']}")
    print(f"Period: {analysis['period_days']} days")
    print()
    
    print("💰 Capital Movements:")
    print(f"  Deposits:     {format_amount(analysis['total_deposits']):>15}  ({analysis['deposit_count']} transactions)")
    print(f"  Withdrawals:  {format_amount(-analysis['total_withdrawals']):>15}  ({analysis['withdrawal_count']} transactions)")
    print(f"  Net Deposits: {format_amount(analysis['net_deposits']):>15}")
    print()
    
    print("🎁 Rewards & Losses:")
    print(f"  Rewards:      {format_amount(analysis['total_rewards']):>15}  ({analysis['reward_count']} transactions)")
    print(f"  Losses:       {format_amount(-analysis['total_losses']):>15}")
    print()
    
    print("📊 Net Change:")
    print(f"  Total:        {format_amount(analysis['net_with_rewards']):>15}")
    print()


def print_transactions(updates: List[LedgerUpdate], title: str, max_show: int = 10):
    """Print transaction table"""
    if not updates:
        return
    
    print(f"\n{title} ({len(updates)} total, showing {min(len(updates), max_show)}):")
    print("-" * 80)
    
    # Prepare table data
    table_data = []
    for update in sorted(updates, key=lambda x: x.time_ms, reverse=True)[:max_show]:
        table_data.append([
            format_timestamp(update.time_ms),
            update.update_type,
            f"${update.amount:,.2f}",
            update.hash[:10] + "..."
        ])
    
    print(tabulate(
        table_data,
        headers=["Time", "Type", "Amount", "Hash"],
        tablefmt="grid"
    ))


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Retrieve and analyze Hyperliquid deposits for a user"
    )
    parser.add_argument(
        "user",
        help="User address (0x...)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to look back (default: 30)"
    )
    parser.add_argument(
        "--include-rewards",
        action="store_true",
        help="Include rewards in deposit totals"
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Show all transactions (default: 10 most recent)"
    )
    
    args = parser.parse_args()
    
    # Validate address
    if not args.user.startswith('0x') or len(args.user) != 42:
        print(f"Error: Invalid address format: {args.user}")
        print("Address must be 42 characters starting with 0x")
        sys.exit(1)
    
    # Create tracker
    tracker = HyperliquidDepositTracker()
    
    # Analyze deposits
    analysis = tracker.analyze_deposits(
        user=args.user,
        days=365,
        include_rewards=args.include_rewards
    )
    
    if not analysis:
        return
    
    # Print summary
    print_summary(analysis)
    
    # Print detailed transactions
    max_show = 999999 if args.show_all else 10
    
    if analysis['deposits']:
        print_transactions(analysis['deposits'], "💵 DEPOSITS", max_show)
    
    if analysis['withdrawals']:
        print_transactions(analysis['withdrawals'], "💸 WITHDRAWALS", max_show)
    
    if analysis['rewards']:
        print_transactions(analysis['rewards'], "🎁 REWARDS", max_show)
    
    if analysis['losses']:
        print_transactions(analysis['losses'], "💀 LOSSES (Liquidations)", max_show)
    
    if analysis['internals']:
        print_transactions(analysis['internals'], "🔄 INTERNAL TRANSFERS", max_show)
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()