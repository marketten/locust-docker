import uuid
import json
import logging
from random import randrange
import sys
from locust import HttpUser, between, task, run_single_user
import time

class WebsiteUser(HttpUser):
    wait_time = between(5, 15)
    host = "http://loadtest.tekmarglobal.com"
    tid = "loadtest"

    def __init__(self, *args, **kwargs):
        super(WebsiteUser, self).__init__(*args, **kwargs)
        self.selectedCity = None
        self.deviceId = None
        self.userToken = None
        self.selectedCounty = None
        self.products = None
        self.selectedNeighborhood = None
        self.regionId = None
        self.minimumCartAmount = None
        self.selectedTimeSlotId = None
        self.addressId = None
        self.headers = {"User-Agent": "Kiler LoadTest User", "x-tid": self.tid,  "Accept-Encoding": "gzip,deflate,br", "Accept": "*/*",
                        "Connection": "keep-alive", "Content-Type": "application/json"}

    @task
    def index(self):
        self.deviceId = str(uuid.uuid4())
        logging.info(self.deviceId + " device Id için teste başlanıldı.")
        self.login()
        self.select_first_neighborhood()
        self.create_cart()
        self.get_catalog()
        self.get_cart()
        self.get_region_info()
        self.register()
        self.add_product()
        self.update_customer()
        self.update_address()
        self.accept_agreement()
        self.get_timeslot()
        self.create_order()

    def login(self):
        response = self.client.post("/api/Account/login", json={
            "sessionId": self.deviceId
        })
        if response.status_code == 200:
            response_json = json.loads(response.text)
            self.userToken = response_json.get("data", {}).get("token")
            self.headers["Authorization"] = "Bearer " + self.userToken
            self.client.headers = self.headers

    def select_first_neighborhood(self):
        self.select_city()
        self.select_county()
        self.select_neighborhood()

    def select_city(self):
        response = self.client.post("/api/Definition/Cities")
        if response.status_code == 200:
            response_json = json.loads(response.text)
            data_list = response_json.get("data", [])
            if len(data_list) != 0:
                pass
            else:
                logging.error("İl bilgisi bulunamadı")

            self.selectedCity = data_list[randrange(len(data_list))]

    def select_county(self):
        print(self.selectedCity)
        logging.debug(self.selectedCity.get("name") + " için ilçeler alınıyor...")
        response = self.client.post("/api/Definition/Counties", json={
            "city": self.selectedCity.get("id")
        })
        if response.status_code == 200:
            data = json.loads(response.text).get("data", [])
            self.selectedCounty = data[randrange(len(data))]

    def select_neighborhood(self):
        logging.debug(self.selectedCounty.get("name") + " için mahalle bilgileri alınıyor...")
        response = self.client.post("/api/Definition/Neighborhood", json={
            "county": self.selectedCounty.get("id")
        })
        if response.status_code == 200:
            data = json.loads(response.text).get("data")
            self.selectedNeighborhood = {"name":"19 Mayıs", "id":3495}
            logging.debug((self.selectedNeighborhood.get("name") + " mahallesi seçildi"))

    def create_cart(self):
        logging.info(self.deviceId + " cihazı için " + self.selectedNeighborhood.get(
            "name") + " mahallesinde sepet oluşturuluyor...")
        response = self.client.post("/api/Cart/CreateCart",
                                    json={
                                        "neighborhoodID": self.selectedNeighborhood.get("id")
                                    })
        if response.status_code == 200:
            data = json.loads(response.text).get("data")

    def get_catalog(self):
        logging.info(self.selectedNeighborhood.get("name") + " mahallesine ait katalog alınıyor")
        response = self.client.get("/api/Catalog/getNeighborhoodCatalog?neighborhood=" +
                                   str(self.selectedNeighborhood.get("id")))
        if response.status_code == 200:
            product_info = []
            data = json.loads(response.text).get("data", {})
            products = data.get("products", [])

            for product in products:
                product_info.append({
                    "productId": product.get("id"),
                    "MaxQuantity": product.get("maxQuantity"),
                    "MinQuantity": product.get("minQuantity"),
                    "Price": product.get("prices", [])[0].get("price")
                })

            def extract_product_info_recursive(categories):
                for category in categories:
                    products = category.get("products")
                    for product in products:
                        product_info.append({
                            "productId": product.get("id"),
                            "MaxQuantity": product.get("maxQuantity"),
                            "MinQuantity": product.get("minQuantity"),
                            "Price": product.get("prices", [])[0].get("price")
                        })
                    extract_product_info_recursive(category.get("subCategories", []))

            categories = data.get("subCategories", [])
            extract_product_info_recursive(categories)
            self.products = product_info

    def get_cart(self):
        response = self.client.post("/api/Cart")
        if response.status_code == 200:
            data = json.loads(response.text).get("data")
            self.regionId = data.get("regionId")

    def get_region_info(self):
        response = self.client.post("/api/Admin/Region?regionId=" + str(self.regionId))
        if response.status_code == 200:
            data = json.loads(response.text).get("data")[0]
            self.minimumCartAmount = data.get("minimunCartAmount")

    def register(self):
        response = self.client.post("/api/Register/SendSms", json={
            "phone": str(self.deviceId)
        })
        if response.status_code == 200:
            data = json.loads(response.text).get("data")
            response = self.client.post("/api/Register/VerifySms", json={
                "phone": data.get("phone"), "smsCode": "1234"
            })
            if response.status_code == 200:
                data = json.loads(response.text).get("data")
                self.userToken = data.get("token")
                self.headers["Authorization"] = "Bearer " + self.userToken

    def add_product(self):
        time.sleep(30)
        selected_product = self.products[randrange(len(self.products))]
        response = self.client.post("/api/Cart/UpdateCart", json={
            "region": self.regionId,
            "productId": selected_product.get("productId"),
            "quantity": selected_product.get("MinQuantity")
        })
        if response.status_code == 200:
            data = json.loads(response.text).get("data")
            if data.get("cartTotal") < self.minimumCartAmount:
                self.add_product()

    def update_customer(self):
        response = self.client.post("/api/Customer/UpdateCustomer", json={
            "name": "LoadTest-" + str(self.deviceId),
            "surname": "Tekmar A.S.",
            "birthDate": "2008-01-01T03:00:00.000Z",
            "email": str(self.deviceId) + "@tekmar.com",
            "gender": 2
        })
        if response.status_code == 200:
            pass

    def update_address(self):
        response = self.client.post("/api/Customer/UpdateAddress", json={
            "name": "LoadTest-" + str(self.deviceId),
            "active": True,
            "neighborhood": self.selectedNeighborhood.get("id"),
            "building": "1",
            "floor": "12",
            "door": "123",
            "description": "TEST description ",
            "customerName": "Load",
            "customerSurname": "Test ",
            "street": "Stres cd",
            "isindividual": True,
            "companyName": "",
            "taxOffice": "",
            "taxNumber": ""
        })
        if response.status_code == 200:
            data = json.loads(response.text).get("data")
            self.addressId = data.get("address")[0].get("addressId")

    def accept_agreement(self):
        response = self.client.post("/api/Definition/UpdateAgreementLog", json={
            "code": "ECAT", "accept": True
        })
        if response.status_code == 200:
            response = self.client.post("/api/Definition/UpdateAgreementLog", json={
                "code": "GDPR", "accept": True
            })
            if response.status_code == 200:
                pass

    def get_timeslot(self):
        response = self.client.post("/api/Cart/GetTimeSlots")
        if response.status_code == 200:
            data = json.loads(response.text).get("data")
            filtered_data = [entry for entry in data if entry['quota'] > 3]
            self.selectedTimeSlotId = (filtered_data[randrange(len(filtered_data))]).get("id")

    def create_order(self):
        response = self.client.post("/api/Order/CreateOrder", json={
            "deliveryAddressId": self.addressId,
            "billingAddressId": self.addressId,
            "timeStotId": self.selectedTimeSlotId,
            "paymentCode": str(uuid.uuid4()),
            "orderNote": "test",
            "paymentTypeCode": "CREDITONDELIVERY"
        })
        if response.status_code == 200:
            pass
