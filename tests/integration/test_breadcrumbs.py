"""
Tests for the admin breadcrumbs-with-icons macro
(app/templates/macros/breadcrumbs.html, daisyUI "breadcrumbs with
icons") shared across every admin page's breadcrumb trail.
"""


class TestBreadcrumbIcons:
    def test_groups_page_breadcrumb_has_icons(self, test_app, logged_in_client):
        resp = logged_in_client.get("/admin/groups")
        body = resp.get_data(as_text=True)

        assert 'class="breadcrumbs' in body
        bc_start = body.index('class="breadcrumbs')
        bc_end = body.index("</div>", bc_start)
        breadcrumb_html = body[bc_start:bc_end]

        # Root "Admin" crumb and the current-page crumb both carry an icon.
        assert "fa-cog" in breadcrumb_html
        assert "fa-user-friends" in breadcrumb_html

    def test_automation_rules_breadcrumb_has_three_levels_with_icons(
        self, test_app, logged_in_client
    ):
        resp = logged_in_client.get("/admin/automation/rules")
        body = resp.get_data(as_text=True)

        bc_start = body.index('class="breadcrumbs')
        bc_end = body.index("</div>", bc_start)
        breadcrumb_html = body[bc_start:bc_end]

        assert "fa-cog" in breadcrumb_html
        assert "fa-robot" in breadcrumb_html
        assert "fa-sliders" in breadcrumb_html
        assert breadcrumb_html.count("<li>") == 3
