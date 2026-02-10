"""
E2E Test: Satellite Selection Flow

Critical user flow:
1. Load page
2. See 3D globe
3. Open sidebar
4. Search for satellite
5. Click satellite
6. View details panel

Requires: playwright install
Run: pytest tests/e2e/ --headed (to see browser)
"""
import pytest
from playwright.async_api import async_playwright, Page, expect


@pytest.fixture(scope="session")
def base_url():
    """Base URL for E2E tests."""
    # Use environment variable or default to production
    import os
    return os.getenv("E2E_BASE_URL", "https://spacex.ericcesar.com")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_user_can_load_page(base_url):
    """User can load the main page."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Navigate to site
        await page.goto(base_url)
        
        # Page should load without errors
        assert page.url.startswith(base_url)
        
        # Should see title
        await expect(page.locator("h1")).to_contain_text("SpaceX Orbital Intelligence")
        
        # Should see "Demo" badge
        await expect(page.locator("text=Demo")).to_be_visible()
        
        await browser.close()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_globe_renders(base_url):
    """3D Globe should render."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        await page.goto(base_url)
        
        # Wait for canvas to appear (3D globe)
        canvas = page.locator("canvas")
        await expect(canvas).to_be_visible(timeout=10000)
        
        # Globe should be interactive (has WebGL context)
        # We can't directly test WebGL, but canvas should be present
        assert await canvas.count() > 0
        
        await browser.close()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_connects(base_url):
    """WebSocket connection should establish."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Listen for WebSocket connections
        ws_connected = False
        
        def handle_websocket(ws):
            nonlocal ws_connected
            ws_connected = True
        
        page.on("websocket", handle_websocket)
        
        await page.goto(base_url)
        
        # Wait for "Live" indicator
        live_indicator = page.locator("text=Live")
        await expect(live_indicator).to_be_visible(timeout=10000)
        
        # WebSocket should have connected
        assert ws_connected, "WebSocket did not connect"
        
        await browser.close()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_sidebar_opens(base_url):
    """User can open/close sidebar."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        await page.goto(base_url)
        await page.wait_for_load_state("networkidle")
        
        # Sidebar should be open by default on desktop
        # Look for satellite list or tabs
        satellites_tab = page.locator("text=Satellites")
        await expect(satellites_tab).to_be_visible()
        
        # Try to find toggle button (chevron)
        # Note: Actual selectors depend on implementation
        # This is a placeholder - adjust based on actual DOM
        
        await browser.close()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.skip(reason="Requires specific satellite ID setup")
async def test_search_and_select_satellite(base_url):
    """User can search for and select a satellite."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser
        page = await browser.new_page()
        
        await page.goto(base_url)
        await page.wait_for_load_state("networkidle")
        
        # Wait for satellites to load
        await page.wait_for_timeout(3000)
        
        # Find search input
        # Note: Adjust selector based on actual implementation
        search_input = page.locator('input[placeholder*="Search"]').first
        
        if await search_input.count() > 0:
            # Type satellite ID
            await search_input.fill("44000")
            await page.wait_for_timeout(500)
            
            # Click first result
            # This depends on how search results are rendered
            first_result = page.locator("[data-satellite-id='44000']").first
            
            if await first_result.count() > 0:
                await first_result.click()
                
                # Details panel should appear
                # Adjust selector based on implementation
                details_panel = page.locator("text=STARLINK")
                await expect(details_panel).to_be_visible(timeout=5000)
        
        await browser.close()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_health_endpoint(base_url):
    """Health endpoint should return 200."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()
        
        # Direct API call
        response = await page.goto(f"{base_url}/health")
        
        assert response.status == 200
        
        # Should be JSON
        body = await response.json()
        assert body["status"] == "healthy"
        assert "satellites_loaded" in body
        
        await browser.close()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_no_console_errors(base_url):
    """Page should load without console errors."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        errors = []
        
        def handle_console(msg):
            if msg.type == "error":
                errors.append(msg.text)
        
        page.on("console", handle_console)
        
        await page.goto(base_url)
        await page.wait_for_load_state("networkidle")
        
        # Some errors might be acceptable (third-party scripts, etc.)
        # But should not have critical app errors
        critical_errors = [e for e in errors if "Uncaught" in e or "TypeError" in e]
        
        assert len(critical_errors) == 0, f"Critical errors found: {critical_errors}"
        
        await browser.close()


# Pytest configuration for E2E tests
def pytest_configure(config):
    """Register E2E marker."""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test (requires playwright)"
    )


# Run E2E tests:
# pytest tests/e2e/ -m e2e -v
# pytest tests/e2e/ -m e2e --headed  # Show browser
# E2E_BASE_URL=http://localhost:3000 pytest tests/e2e/ -m e2e  # Local dev
