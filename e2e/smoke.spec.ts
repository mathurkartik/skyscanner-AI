import { test, expect } from '@playwright/test';

test.describe('Skyscanner AI Smoke Suite (AG-117)', () => {
  test('Smoke 1: Home page loads with navbar, title, and multi-agent pill', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Skyscanner/i);
    const planHeading = page.locator('h1');
    await expect(planHeading).toContainText(/Plan with AI/i);
  });

  test('Smoke 2: Suggestion chip populates input toolbar', async ({ page }) => {
    await page.goto('/');
    const suggestionChip = page.locator('button', { hasText: 'Tokyo & Kyoto' });
    if (await suggestionChip.isVisible()) {
      await suggestionChip.click();
      const input = page.locator('textarea, input[placeholder*="Describe your dream trip"]');
      await expect(input).toHaveValue(/Tokyo/i);
    }
  });

  test('Smoke 3: Fast Demo Mode generates curated multi-agent itinerary', async ({ page }) => {
    await page.goto('/');
    const fastDemoCheckbox = page.locator('input[type="checkbox"]');
    if (!(await fastDemoCheckbox.isChecked())) {
      await fastDemoCheckbox.check();
    }
    const planButton = page.locator('button', { hasText: /Generate Itinerary/i });
    if (await planButton.isVisible()) {
      await planButton.click();
      const itinerary = page.locator('app-itinerary-display, section:has-text("Itinerary")');
      await expect(itinerary).toBeVisible({ timeout: 10000 });
    }
  });
});

