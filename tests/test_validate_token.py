import time

import pytest
from demoproj.core.config import settings
from httpx import AsyncClient
from main import app, azure_scheme
from tests.utils import (
    build_access_token,
    build_access_token_expired,
    build_access_token_guest,
    build_access_token_invalid_claims,
)

from fastapi_azure_auth.auth import AzureAuthorizationCodeBearer


@pytest.mark.asyncio
async def test_normal_user(mock_openid_and_keys, freezer):
    issued_at = int(time.time())
    expires = issued_at + 3600
    async with AsyncClient(
        app=app, base_url='http://test', headers={'Authorization': 'Bearer ' + build_access_token()}
    ) as ac:
        response = await ac.get('api/v1/hello')
    assert response.json() == {
        'hello': 'world',
        'user': {
            'aud': 'api://oauth299-9999-9999-abcd-efghijkl1234567890',
            'family_name': 'Krüger Svensson',
            'given_name': 'Jonas',
            'ipaddr': '192.168.0.0',
            'roles': [],
            'tid': 'intility_tenant_id',
            'unique_name': 'jonas',
            'claims': {
                'acr': '1',
                'aio': 'hello',
                'amr': ['pwd'],
                'appid': '11111111-1111-1111-1111-111111111111',
                'appidacr': '0',
                'aud': 'api://oauth299-9999-9999-abcd-efghijkl1234567890',
                'exp': expires,
                'family_name': 'Krüger Svensson',
                'given_name': 'Jonas',
                'iat': issued_at,
                'in_corp': 'true',
                'ipaddr': '192.168.0.0',
                'iss': 'https://sts.windows.net/intility_tenant_id/',
                'name': 'Jonas Krüger Svensson / Intility AS',
                'nbf': issued_at,
                'oid': '22222222-2222-2222-2222-222222222222',
                'onprem_sid': 'S-1-2-34-5678901234-5678901234-456789012-34567',
                'rh': '0.hellomylittletokenfriendwhatsupwi-thyoutodayheheiho.',
                'scp': 'user_impersonation',
                'sub': '5ZGASZqgF1taj9GlxDHOpeIJjWlyZJwD3mnZBoz9XVc',
                'tid': 'intility_tenant_id',
                'unique_name': 'jonas',
                'upn': 'jonas@cool',
                'uti': 'abcdefghijkl-mnopqrstu',
                'ver': '1.0',
            },
            'upn': 'jonas@cool',
        },
    }


@pytest.mark.asyncio
async def test_guest_user(mock_openid_and_keys):
    azure_scheme_no_guest = AzureAuthorizationCodeBearer(
        app=app,
        app_client_id=settings.APP_CLIENT_ID,
        scopes={
            f'api://{settings.APP_CLIENT_ID}/user_impersonation': '**No client secret needed, leave blank**',
        },
        allow_guest_users=False,
    )
    app.dependency_overrides[azure_scheme] = azure_scheme_no_guest
    async with AsyncClient(
        app=app, base_url='http://test', headers={'Authorization': 'Bearer ' + build_access_token_guest()}
    ) as ac:
        response = await ac.get('api/v1/hello')
    assert response.json() == {'detail': 'Guest users not allowed'}


@pytest.mark.asyncio
async def test_no_keys_to_decode_with(mock_openid_and_empty_keys):
    async with AsyncClient(
        app=app, base_url='http://test', headers={'Authorization': 'Bearer ' + build_access_token()}
    ) as ac:
        response = await ac.get('api/v1/hello')
    assert response.json() == {'detail': 'Unable to verify token, no signing keys found'}


async def test_invalid_token_claims(mock_openid_and_keys):
    async with AsyncClient(
        app=app, base_url='http://test', headers={'Authorization': 'Bearer ' + build_access_token_invalid_claims()}
    ) as ac:
        response = await ac.get('api/v1/hello')
    assert response.json() == {'detail': 'Token contains invalid claims'}


async def test_no_valid_keys_for_token(mock_openid_and_no_valid_keys):
    async with AsyncClient(
        app=app, base_url='http://test', headers={'Authorization': 'Bearer ' + build_access_token_invalid_claims()}
    ) as ac:
        response = await ac.get('api/v1/hello')
    assert response.json() == {'detail': 'Unable to validate token'}


async def test_expired_token(mock_openid_and_keys):
    async with AsyncClient(
        app=app, base_url='http://test', headers={'Authorization': 'Bearer ' + build_access_token_expired()}
    ) as ac:
        response = await ac.get('api/v1/hello')
    assert response.json() == {'detail': 'Token signature has expired'}


async def test_exception_raised(mock_openid_and_keys, mocker):
    mocker.patch('fastapi_azure_auth.auth.jwt.decode', side_effect=ValueError('lol'))
    async with AsyncClient(
        app=app, base_url='http://test', headers={'Authorization': 'Bearer ' + build_access_token_expired()}
    ) as ac:
        response = await ac.get('api/v1/hello')
    assert response.json() == {'detail': 'Unable to process token'}
