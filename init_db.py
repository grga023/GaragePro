"""Create the database schema and (optionally) seed demo data.

Usage:
    python init_db.py            # just create tables
    python init_db.py --demo     # create tables + demo users, cars, services
    python init_db.py --reset     # drop everything first (DANGER)
"""
import argparse
from datetime import date, timedelta

from app import create_app
from app.extensions import db
from app.models import (
    User, Company, Car, Service, Part, Shop,
    ROLE_MODERATOR, ROLE_ADMIN, ROLE_WORKER,
    SERVICE_TYPE_POPRAVKE, SERVICE_TYPE_VULKANIZERSKI, SERVICE_TYPE_MALI_SERVIS,
)


def seed_demo():
    if User.query.count() > 0:
        print("Baza već sadrži korisnike — preskačem demo podatke.")
        return

    # Create a shop (tenant)
    shop = Shop(name="Auto Servis Petrović",
                address="Bulevar oslobođenja 12, Novi Sad",
                contact="021/123-456 • info@servis.rs")
    db.session.add(shop)
    db.session.commit()

    # Legacy company row (backward compat)
    company = Company(id=1, name=shop.name, address=shop.address, contact=shop.contact)
    db.session.add(company)

    moderator = User(full_name="System Moderator", username="moderator",
                     email="moderator@servis.rs", role=ROLE_MODERATOR)
    moderator.set_password("moderator123")
    admin = User(full_name="Marko Petrović", username="admin",
                 email="admin@servis.rs", role=ROLE_ADMIN, shop_id=shop.id)
    admin.set_password("admin123")
    worker = User(full_name="Jovan Jovanović", username="radnik",
                  email="radnik@servis.rs", role=ROLE_WORKER, shop_id=shop.id)
    worker.set_password("radnik123")
    db.session.add_all([moderator, admin, worker])
    db.session.commit()

    car1 = Car(plate="NS123AB", owner_name="Petar Perić", phone="063/111-2222",
               brand="BMW", model="320", engine="2.0", fuel_type="dizel",
               year=2020, mileage=145000, shop_id=shop.id)
    car2 = Car(plate="BG456CD", owner_name="Ana Anić", phone="064/333-4444",
               brand="VW", model="Golf 7", engine="1.6", fuel_type="dizel",
               year=2017, mileage=210000, shop_id=shop.id)
    db.session.add_all([car1, car2])
    db.session.commit()

    s1 = Service(car_id=car1.id, worker_id=admin.id, shop_id=shop.id, date=date.today(),
                 mileage=145000, labor_price=4000,
                 service_type=SERVICE_TYPE_MALI_SERVIS,
                 labor_description="Zamena ulja i filtera")
    s1.parts = [
        Part(name="Motorno ulje 5W30 (5L)", quantity=1, price=6500, price_with_discount=4800),
        Part(name="Filter ulja", quantity=1, price=1200, price_with_discount=800),
        Part(name="Filter vazduha", quantity=1, price=1500, price_with_discount=1000),
    ]

    s2 = Service(car_id=car1.id, worker_id=worker.id, shop_id=shop.id,
                 date=date.today() - timedelta(days=20),
                 mileage=142000, labor_price=8000,
                 service_type=SERVICE_TYPE_POPRAVKE,
                 labor_description="Zamena pločica i diskova (prednji)")
    s2.parts = [
        Part(name="Pločice prednje", quantity=1, price=5500, price_with_discount=3800),
        Part(name="Diskovi prednji (par)", quantity=1, price=9000, price_with_discount=6500),
    ]

    s3 = Service(car_id=car2.id, worker_id=worker.id, shop_id=shop.id, date=date.today(),
                 mileage=210000, labor_price=3000,
                 service_type=SERVICE_TYPE_POPRAVKE,
                 labor_description="Zamena akumulatora")
    s3.parts = [
        Part(name="Akumulator 72Ah", quantity=1, price=14000, price_with_discount=10500),
    ]

    s4 = Service(car_id=car2.id, worker_id=admin.id, shop_id=shop.id,
                 date=date.today() - timedelta(days=5),
                 mileage=209500, labor_price=2500,
                 service_type=SERVICE_TYPE_VULKANIZERSKI,
                 labor_description="Zamena zimskih guma, balansiranje")
    s4.parts = [
        Part(name="Zimske gume 205/55 R16 (4 kom)", quantity=4, price=5500, price_with_discount=4200),
        Part(name="Ventili", quantity=4, price=200, price_with_discount=100),
    ]

    s5 = Service(car_id=car1.id, worker_id=worker.id, shop_id=shop.id,
                 date=date.today() - timedelta(days=3),
                 mileage=144500, labor_price=1500,
                 service_type=SERVICE_TYPE_VULKANIZERSKI,
                 labor_description="Krpljenje gume, balansiranje")
    s5.parts = [
        Part(name="Zakrpa za gumu", quantity=1, price=500, price_with_discount=200),
    ]

    db.session.add_all([s1, s2, s3, s4, s5])
    db.session.commit()
    print("Demo podaci kreirani.")
    print("  Moderator -> korisnik: moderator  lozinka: moderator123")
    print("  Admin     -> korisnik: admin      lozinka: admin123")
    print("  Radnik    -> korisnik: radnik     lozinka: radnik123")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="seed demo data")
    parser.add_argument("--reset", action="store_true", help="drop all tables first")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.reset:
            db.drop_all()
            print("Sve tabele obrisane.")
        db.create_all()
        print("Šema baze je kreirana/ažurirana.")
        if args.demo:
            seed_demo()


if __name__ == "__main__":
    main()
