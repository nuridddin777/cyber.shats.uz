# Multiple Chest Openings (5x) Implementation

The user requested the ability to open 5 chests at once, with an aggregated result summary to increase trust and reliability.

## Proposed Changes

### Backend (shop_routes.py)
- Modify /api/chests/open/tariff and /api/chests/open/id routes to accept a qty parameter (default 1, allowed values 1 or 5).
- If qty > 1, loop the chest opening logic qty times.
- Aggregate the results and return them inside {"results": [...list of individual results...], "total_keys": X, "opened": Y}.
- If tickets run out midway (e.g. user had 3 tickets but requested 5), it will safely open 3 and return those results.

### Frontend (	emplates/chests.html)
#### UI Buttons
- [MODIFY] chests.html: Add a new "5 tadan ochish" (Open 5x) button next to the "1 ta ochish" button for both the Tariff and ID Chest sections.
- Update the onclick handler to pass qty to the openChest function.

#### JS Logic
- [MODIFY] openChest(type, qty=1): Update the etch body to send JSON.stringify({qty: qty}) or FormData containing the qty.
- [MODIFY] showChestResult(type, data, qty): Update the modal rendering logic:
  - If qty == 1: use the existing UI layout.
  - If qty > 1: render a scrollable list of what was dropped from each of the chests (e.g., #1: 5 kalit, #2: 8 kalit, etc.).
  - Show the **Grand Total** prominently at the top of the modal (e.g., "Jami: 25 kalit tushdi!").

## Verification Plan
1. Check that the UI correctly displays the new buttons.
2. Ensure the user can buy 10 tickets, and then successfully open 5 tickets in one click.
3. Verify the modal correctly aggregates the total keys and lists all the individual drops.
4. Verify database ticket balances subtract by 5, and key balances increase by the aggregated amount.
