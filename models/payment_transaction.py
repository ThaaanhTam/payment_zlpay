import logging
import json
import hmac
import hashlib
import urllib.parse
from datetime import datetime
from time import time
import random

from werkzeug import urls
from odoo import _, api, fields, models
from odoo.addons.payment_zlpay import const
from odoo.http import request
_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"
    app_trans_id = fields.Char(string="App Transaction ID")
    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != "zlpay":
            return res

        base_url = self.provider_id.get_base_url()
        int_amount = int(self.amount)

        # Tạo ID giao dịch và thời gian hiện tại
        trans_id = random.randrange(1000000)
        app_time = int(round(time() * 1000))  # Thời gian hiện tại tính bằng mili giây

       # Lấy các mục từ đơn hàng
        order_items = []
        for line in self.invoice_ids.mapped('invoice_line_ids'):
            item = {
                "id": line.id,
                "name": line.name,
                "price": int(line.price_unit * 100)  # Giá sản phẩm tính bằng xu
            }
            order_items.append(item)
        # Tạo đơn hàng
        order = {
            "app_id": self.provider_id.appid,
            "app_trans_id": "{:%y%m%d}_{}".format(datetime.today(), trans_id),
            "app_user": self.provider_id.app_user,
            "app_time": app_time,
            "embed_data": json.dumps({"redirecturl": urls.url_join(base_url, '/payment/zlpay/return')}),
            "item": json.dumps(order_items),
            "amount": int_amount,
            "description": f"Lazada - Payment for the order #{trans_id}",
            "bank_code": "",
            "callback_url": urls.url_join(base_url, '/payment/zlpay/callback'),  # URL callback
        }

        # Chuỗi dữ liệu để tạo chữ ký
        data = "{}|{}|{}|{}|{}|{}|{}".format(
            order["app_id"], order["app_trans_id"], order["app_user"],
            order["amount"], order["app_time"], order["embed_data"], order["item"]
        )

        # Tạo chữ ký (mac)
        order["mac"] = hmac.new(self.provider_id.key1.encode(), data.encode(), hashlib.sha256).hexdigest()

        # Gửi yêu cầu tạo đơn hàng đến ZaloPay
        try:
            response = urllib.request.urlopen(url="https://sb-openapi.zalopay.vn/v2/create", data=urllib.parse.urlencode(order).encode())
            result = json.loads(response.read())
            _logger.info("Tạo hóa đơn thành công 12213: %s", result)
            # Cập nhật trường app_trans_id
            self.write({
                'app_trans_id': order['app_trans_id']
            })
        except Exception as e:
            _logger.error("ZaloPay create order failed: %s", e)
            raise ValidationError(_("fffffffffffffffffffffffff: %s") % e)

        # Trả về các giá trị cần thiết để hiển thị
        rendering_values = {
            "api_url": result.get("order_url"),
        }
        return rendering_values
    


    def _get_tx_from_notification_data(self, provider_code, notification_data):
        _logger.info("Starting _get_tx_from_notification_data with provider_codeaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa: %s, notification_data: %s", provider_code, notification_data)
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != "zlpay" or len(tx) == 1:
            _logger.info("Provider code is not zlpay or transaction length is 1, returning taaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaax: %s", tx)
            return tx

        reference = notification_data.get("app_trans_id")
        if not reference:
            _logger.error("ZaloPay: Received data aaaaaawith missing reference.")
            raise ValidationError(
                "ZaloPay: " + _("Received data with missing reference.")
            )

        tx = self.search(
            [("app_trans_id", "=", reference), ("provider_code", "=", "zlpay")]
        )
        if not tx:
            _logger.error("ZaloPay: No transaction found matching reference %s.", reference)
            raise ValidationError(
                "ZaloPay: " + _("No transaction found matching reference %s.", reference)
            )
        _logger.info("Transaction found: %s", tx)
        return tx
    


