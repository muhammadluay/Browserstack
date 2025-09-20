import os


def test_title_smoke(driver):
    url = os.getenv("TEST_URL", "https://www.example.com")
    expected = os.getenv("ASSERT_TITLE_CONTAINS")

    driver.get(url)

    title = driver.title or ""

    try:
        if expected:
            assert expected in title, f"Expected '{expected}' in title '{title}'"
            reason = f"Title contains '{expected}'"
        else:
            assert len(title) > 0, "Page title should not be empty"
            reason = "Title is non-empty"
        status = "passed"
    except AssertionError as e:
        status = "failed"
        reason = str(e)
        raise
    finally:
        # Report status to BrowserStack session dashboard
        driver.execute_script(
            'browserstack_executor: {"action": "setSessionStatus", "arguments": {"status":"%s", "reason": "%s"}}'
            % (status, reason.replace('"', "'"))
        )

