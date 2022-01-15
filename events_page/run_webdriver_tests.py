#!/usr/bin/env python
import os

from logzero import logger
from selenium import webdriver

from app import get_base_url


def run_webdriver_tests(
    base_url,
    user_name,
    access_key,
    build_name,
    project_name,
    screenshot_path="webdriver_test_screenshot.png",
):
    desired_cap = {
        "os": "Windows",
        "os_version": "10",
        "browser": "Chrome",
        "browser_version": "latest",
        "browserstack.local": "false",
        "build": build_name,
        "project": project_name,
    }
    driver = webdriver.Remote(
        command_executor=f"https://{user_name}:{access_key}@hub-cloud.browserstack.com/wd/hub",
        desired_capabilities=desired_cap,
    )
    logger.info(f"Using remote webdriver for test against: {base_url}")
    driver.get(base_url)
    logger.debug(f"{driver.title}")
    logger.info(f"Saving test screenshot to: {screenshot_path=}")
    driver.save_screenshot(screenshot_path)
    driver.quit()


if __name__ == "__main__":
    import cli
    from config import cfg

    cfg.load()
    parser = cli.build_parser()
    args = cli.parse_args(parser)
    run_webdriver_tests(
        base_url=get_base_url(),
        user_name=os.environ["BROWSERSTACK_USERNAME"],
        access_key=os.environ["BROWSERSTACK_ACCESS_KEY"],
        build_name=os.getenv("BROWSERSTACK_BUILD_NAME", "UNKNOWN"),
        project_name=os.environ.get("BROWSERSTACK_PROJECT_NAME", "lv-events-page"),
    )

# import unittest
# from selenium import webdriver
# from selenium.webdriver.common.keys import Keys

# class PythonOrgSearch(unittest.TestCase):

#     def setUp(self):
#         self.driver = webdriver.Firefox()

#     def test_search_in_python_org(self):
#         driver = self.driver
#         driver.get("http://www.python.org")
#         self.assertIn("Python", driver.title)
#         elem = driver.find_element_by_name("q")
#         elem.send_keys("pycon")
#         elem.send_keys(Keys.RETURN)
#         assert "No results found." not in driver.page_source


#     def tearDown(self):
#         self.driver.close()

# if __name__ == "__main__":
#     unittest.main()
