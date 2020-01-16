import pytest
from bs4 import BeautifulSoup


@pytest.mark.vcr()
def test_register(client):
    """Register a user"""
    result = client.post(
        '/register',
        data={
            "firstname": "First",
            "lastname": "Last",
            "username": "dummy",
            "password": "password",
            "password_confirm": "password",
        },
        follow_redirects=True,
    )
    assert result.status_code == 200
    page = BeautifulSoup(result.data, 'html.parser')
    messages = page.select(".flash-messages .green")
    assert len(messages) == 1
    assert (
        messages[0].get_text(strip=True)
        == 'Congratulations, you now have an account! Go ahead and sign in to proceed.'
    )
