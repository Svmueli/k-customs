import Link from "next/link";

import CheckoutForm from "@/features/checkout/components/CheckoutForm";

export default function CheckoutPage() {
  return (
    <main>
      <section className="kc-checkout-page">
        <div className="kc-container">

          <div className="kc-checkout-header">
            <div>
              <span className="kc-eyebrow">
                KimCustoms checkout
              </span>

              <h1>
                Let&apos;s make it yours.
              </h1>

              <p>
                Enter your details below and
                we&apos;ll prepare your personalized
                order.
              </p>
            </div>

            <Link
              href="/shop/cart"
              className="kc-checkout-back"
            >
              ← Back to your bag
            </Link>
          </div>

          <CheckoutForm />

        </div>
      </section>
    </main>
  );
}
