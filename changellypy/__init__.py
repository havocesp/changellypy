"""
Changelly API wrapper module for Python 3

Author:     Daniel J. Umpierrez
Version:    0.1.0a
License:    MIT
Site:       https://github.com/havocesp/changellypy
"""

import hashlib
import hmac
import json

import requests as req

API_URL = 'https://api.changelly.com'

__author__ = 'Daniel J. Umpierrez'
__version__ = '0.1.0a'
__package__ = 'changellypy'
__all__ = ['ChangellyPy']


class ChangellyPy:
    """
    Changelly API Wrapper
    """
    _headers = {
        'api-key': str(),
        'sign': str(),
        'Content-type': 'application/json'
    }

    currency_list = list()

    def __init__(self, key, secret):
        """
        Class constructor.

        :param str key: API key provided by Changelly
        :param str secret:
        """
        self._secret = secret.encode('utf-8')
        self._headers['api-key'] = key

    def _request(self, command, params=None):
        """
        API request handler.

        :param str command: REST API end point command.
        :param list, dict params:
        :return list, dict:
        """
        data = json.dumps({
            'jsonrpc': '2.0',
            'id': 1,
            'method': command,
            'params': params if params is not None else []
        })

        self._headers['sign'] = hmac.new(self._secret, data.encode('utf-8'), hashlib.sha512).hexdigest()

        response = req.post(API_URL, headers=self._headers, data=data)

        if response.ok:
            return response.json().get('result')
        else:
            response.raise_for_status()

    def get_currencies(self):
        """
        Query supported currency list from Changelly.

        :return list: a supported currency list
        """
        if len(self.currency_list) == 0:
            self.currency_list = self._request('getCurrencies')
        return self.currency_list

    def get_min_amount(self, from_currency, to_currency):
        """
        Query the min. "from currency" amount required for a transaction.

        :param str from_currency: "from" currency name
        :param str to_currency: "to" currency name
        """
        from_currency = from_currency.lower()
        to_currency = to_currency.lower()

        if from_currency in self.get_currencies() and to_currency in self.get_currencies():
            params = {
                'from': from_currency,
                'to': to_currency
            }
            return round(float(self._request('getMinAmount', params)), 8)
        else:
            raise ValueError('Invalid currency error.')

    def get_exchange_amount(self, from_currency, to_currency, amount):
        """
        Extra API fee is included in "amount".

        :param str, list from_currency: "from" currency name list (size should fit to_currency size) or str
        :param str, list to_currency: "to" currency name list (size should fit from_currency size) or str
        :param float amount: "from" currency amount
        :return list, float: list of dict (records) or just a float if just 1 to 1 currency is set as params
        """
        if from_currency is not None and isinstance(from_currency, str):
            from_currency = [from_currency]
        from_currency = [*map(str.lower, from_currency)]

        if to_currency is not None and isinstance(to_currency, str):
            to_currency = [to_currency]
        to_currency = [*map(str.lower, to_currency)]

        amount = float(str(amount))

        for f, t in zip(from_currency, to_currency):
            if all((f in self.get_currencies(), t in self.get_currencies())):
                min_amount = self.get_min_amount(f, t)
                if amount < min_amount:
                    raise ValueError('Min. mount is amount {:.8f} {}.'.format(min_amount, f.upper()))
            else:
                raise ValueError('Invalid currency error.')

        from_size, to_size = len(from_currency), len(to_currency)

        if from_size != to_size:
            raise IndexError('"From" and "To" lists do not have the same size.')
        elif from_size == 1:
            params = {'from': from_currency[0], 'to': to_currency[0], 'amount': amount}
        else:
            params = list()
            for f, t in zip(from_currency, to_currency):
                params.append({'from': f, 'to': t, 'amount': amount})

        result = self._request('getExchangeAmount', params)

        elements_count = len(result)

        if isinstance(result, str):
            return round(float(result), 8)
        else:
            for idx in range(0, elements_count):
                result[idx]['amount'] = round(float(result[idx]['amount']), 8)
            return result

    def create_transaction(
            self,
            from_currency,
            to_currency,
            destination_address,
            amount,
            extra_id=None,
            refund_address=None,
            refund_extra_id=None
    ):
        """
        Create a new transaction.

        :param str from_currency: from currency name
        :param str to_currency: to currency name
        :param str destination_address: destination currency wallet address
        :param float amount: amount to exchange
        :param str extra_id: if currency supports or require an extra "id" put it in this param
        :param str refund_address: destination currency wallet address in case of refund (optional)
        :param str refund_extra_id: destination currency wallet address extra "id" in case of refund (optional)
        :return str: if success, a transaction ID will be returned
        """
        if extra_id is None:
            extra_id = 'null'

        params = {
            'from': from_currency,
            'to': to_currency,
            'address': destination_address,
            'extraId': extra_id,
            'amount': amount
        }

        if all((refund_address is not None, isinstance(refund_address, str), len(refund_address) > 0)):
            params.update(refundAddress=refund_address)

        if all((refund_extra_id is not None, isinstance(refund_extra_id, str), len(refund_extra_id) > 0)):
            params.update(refundExtraId=refund_extra_id)

        tx_id = self._request('createTransaction', params)
        return tx_id

    def get_transaction_status(self, tx_id):
        """
        Possible states are:
            'confirming'	Your transaction is in a mempool and waits to be confirmed.
            'exchanging'	Your payment is received and being exchanged via our partner.
            'sending'	    Money is sending to the recipient address.
            'finished'	    Money is successfully sent to the recipient address.
            'failed'	    Transaction has failed. In most cases, the amount was less than the minimum.
            'refunded'	    Exchange was failed and coins were refunded to user's wallet.  The wallet
                            address should be provided by user.

        :param str tx_id: the transaction id
        :return str: current transaction state
        """
        params = {'id': str(tx_id)}
        return self._request('getStatus', params)
