"use client";

import { FormEvent, useState } from "react";

import Link from "next/link";

import { FiArrowRight, FiCheck, FiLock, FiTruck } from "react-icons/fi";

import { useCart } from "@/features/cart/context/CartContext";

import {
  createOrder,
  type CreateOrderResponse,
} from "@/features/orders/api/createOrder";
import { initiateMpesaPayment } from "@/features/orders/api/initiateMpesaPayment";

export default function CheckoutForm() {
  const {
    items,
    itemCount,
    subtotal,
    clearCart,
  } = useCart();

  const [paymentMethod, setPaymentMethod] =
    useState<"mpesa" | "card" | "cash">("mpesa");

  const [submitting, setSubmitting] =
    useState(false);

  const [success, setSuccess] =
    useState(false);

  const [formError, setFormError] =
    useState("");

  const [createdOrder, setCreatedOrder] =
    useState<CreateOrderResponse | null>(null);

  const [form, setForm] = useState({
    firstName: "",
    lastName: "",
    phone: "",
    email: "",
    county: "",
    town: "",
    address: "",
    notes: "",
  });

  const handleChange = (
    event: React.ChangeEvent<
      HTMLInputElement |
      HTMLTextAreaElement |
      HTMLSelectElement
    >
  ) => {
    const { name, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
    }));

    setFormError("");
  };

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    setFormError("");

    if (items.length === 0) {
      setFormError(
        "Your bag is empty. Add an item before checking out."
      );

      return;
    }

    setSubmitting(true);

    let orderWasCreated = Boolean(createdOrder);

    try {
      const order = createdOrder || await createOrder({
        firstName: form.firstName,
        lastName: form.lastName,
        phone: form.phone,
        email: form.email,

        county: form.county,
        town: form.town,
        address: form.address,
        notes: form.notes,

        paymentMethod,
        items,
      });

      setCreatedOrder(order);
      orderWasCreated = true;

      if (paymentMethod === "mpesa") {
        await initiateMpesaPayment(order.payment_token, form.phone);
      }

      setSuccess(true);
      clearCart();
    } catch (error) {
      console.error(
        "Checkout error:",
        error
      );

      setFormError(orderWasCreated
        ? "Your order was created, but we could not send the M-Pesa prompt. Check your phone number and retry payment."
        : "We couldn’t create your order. Please check your details and try again."
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="kc-checkout-success">

        <div className="kc-checkout-success-icon">
          <FiCheck size={25} />
        </div>

        <span className="kc-eyebrow">
          {paymentMethod === "mpesa" ? "Payment prompt sent" : "Order received"}
        </span>

        <h2>
          {paymentMethod === "mpesa" ? "One small step left." : "You&apos;re all set."}
        </h2>

        <p>
          {paymentMethod === "mpesa"
            ? "Check your phone and enter your M-Pesa PIN to complete payment."
            : "Your order has been received. We will contact you with the next payment steps."}
        </p>

        {createdOrder && (
          <p className="kc-order-reference">
            Order reference <strong>{createdOrder.order_number}</strong>
          </p>
        )}

        <Link
          href="/"
          className="kc-btn kc-btn-rose"
        >
          Back to KimCustoms
          <FiArrowRight size={17} />
        </Link>

      </div>
    );
  }

  return (
    <form
      className="kc-checkout-layout"
      onSubmit={handleSubmit}
    >

      {/* =================================
          MAIN FORM
      ================================= */}

      <div className="kc-checkout-main">

        <div className="kc-checkout-reassurance" aria-label="Checkout benefits">
          <span><FiLock size={15} /> Secure payment</span>
          <span><FiTruck size={16} /> Crafted with care in Kenya</span>
        </div>

        {/* CUSTOMER DETAILS */}

        <section className="kc-checkout-section">

          <div className="kc-checkout-section-heading">
            <span className="kc-form-step">
              1
            </span>

            <div>
              <h2>
                Your details
              </h2>

              <p>
                Tell us where we should reach you.
              </p>
            </div>
          </div>

          <div className="kc-checkout-grid">

            <div className="kc-field">
              <label htmlFor="firstName">
                First name
              </label>

              <input
                id="firstName"
                name="firstName"
                type="text"
                autoComplete="given-name"
                value={form.firstName}
                onChange={handleChange}
                required
              />
            </div>

            <div className="kc-field">
              <label htmlFor="lastName">
                Last name
              </label>

              <input
                id="lastName"
                name="lastName"
                type="text"
                autoComplete="family-name"
                value={form.lastName}
                onChange={handleChange}
                required
              />
            </div>

            <div className="kc-field">
              <label htmlFor="phone">
                M-Pesa / phone number
              </label>

              <input
                id="phone"
                name="phone"
                type="tel"
                inputMode="tel"
                autoComplete="tel"
                placeholder="07XX XXX XXX"
                value={form.phone}
                onChange={handleChange}
                required
              />

              <span>
                We&apos;ll use this number for
                order updates and payment.
              </span>
            </div>

            <div className="kc-field">
              <label htmlFor="email">
                Email address
              </label>

              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={form.email}
                onChange={handleChange}
                required
              />
            </div>

          </div>
        </section>

        {/* DELIVERY */}

        <section className="kc-checkout-section">

          <div className="kc-checkout-section-heading">
            <span className="kc-form-step">
              2
            </span>

            <div>
              <h2>
                Delivery
              </h2>

              <p>
                Where should we deliver your
                keepsake?
              </p>
            </div>
          </div>

          <div className="kc-checkout-grid">

            <div className="kc-field kc-field-full">
              <label htmlFor="county">
                County
              </label>

              <select
                id="county"
                name="county"
                value={form.county}
                onChange={handleChange}
                required
              >
                <option value="">
                  Select your county
                </option>

                <option value="Nairobi">
                  Nairobi
                </option>

                <option value="Mombasa">
                  Mombasa
                </option>

                <option value="Kiambu">
                  Kiambu
                </option>

                <option value="Nakuru">
                  Nakuru
                </option>

                <option value="Machakos">
                  Machakos
                </option>

                <option value="Kajiado">
                  Kajiado
                </option>

                <option value="Kitui">
                  Kitui
                </option>

                <option value="Kakamega">
                  Kakamega
                </option>

                <option value="Kisumu">
                  Kisumu
                </option>

                <option value="Uasin Gishu">
                  Uasin Gishu
                </option>

                <option value="Other">
                  Other
                </option>
              </select>
            </div>

            <div className="kc-field">
              <label htmlFor="town">
                Town / Area
              </label>

              <input
                id="town"
                name="town"
                type="text"
                value={form.town}
                onChange={handleChange}
                placeholder="e.g. Westlands"
                required
              />
            </div>

            <div className="kc-field">
              <label htmlFor="address">
                Delivery address
              </label>

              <input
                id="address"
                name="address"
                type="text"
                value={form.address}
                onChange={handleChange}
                placeholder="Building, street, landmark..."
                required
              />
            </div>

            <div className="kc-field kc-field-full">
              <label htmlFor="notes">
                Delivery notes
                <span>Optional</span>
              </label>

              <textarea
                id="notes"
                name="notes"
                rows={3}
                value={form.notes}
                onChange={handleChange}
                placeholder="Anything our delivery team should know?"
              />
            </div>

          </div>
        </section>

        {/* PAYMENT */}

        <section className="kc-checkout-section">

          <div className="kc-checkout-section-heading">
            <span className="kc-form-step">
              3
            </span>

            <div>
              <h2>
                Payment
              </h2>

              <p>
                Choose your preferred payment method.
              </p>
            </div>
          </div>

          <div className="kc-payment-options">

            {/* M-PESA */}

            <label
              className={`kc-payment-option ${
                paymentMethod === "mpesa"
                  ? "active"
                  : ""
              }`}
            >
              <input
                type="radio"
                name="payment"
                value="mpesa"
                checked={
                  paymentMethod === "mpesa"
                }
                onChange={() =>
                  setPaymentMethod("mpesa")
                }
              />

              <div className="kc-payment-icon kc-payment-icon-mpesa">
                <span>
                  M
                </span>
              </div>

              <div className="kc-payment-content">
                <strong>
                  M-Pesa
                </strong>

                <span>
                  Pay securely using
                  Safaricom M-Pesa.
                </span>
              </div>

              <span className="kc-payment-badge">
                Recommended
              </span>
            </label>

            {/* CARD */}

            <label
              className="kc-payment-option is-unavailable"
            >
              <input
                type="radio"
                name="payment"
                value="card"
                disabled
              />

              <div className="kc-payment-icon kc-payment-icon-card">
                <span>
                  CARD
                </span>
              </div>

              <div className="kc-payment-content">
                <strong>
                  Card payment
                </strong>

                <span>
                  Card payments will be available soon.
                </span>

                <div className="kc-card-brands">
                  <span className="kc-card-brand visa">
                    VISA
                  </span>

                  <span className="kc-card-brand mastercard">
                    <i />
                    <i />
                    <small>
                      Mastercard
                    </small>
                  </span>
                </div>
              </div>

              <span className="kc-payment-secure">
                Coming soon
              </span>
            </label>

            {/* CASH ON DELIVERY */}

            <label
              className={`kc-payment-option ${
                paymentMethod === "cash"
                  ? "active"
                  : ""
              }`}
            >
              <input
                type="radio"
                name="payment"
                value="cash"
                checked={
                  paymentMethod === "cash"
                }
                onChange={() =>
                  setPaymentMethod("cash")
                }
              />

              <div className="kc-payment-icon kc-payment-icon-cash">
                <span>
                  KSh
                </span>
              </div>

              <div className="kc-payment-content">
                <strong>
                  Cash on delivery
                </strong>

                <span>
                  Pay when your order is delivered.
                  Available for eligible orders.
                </span>
              </div>
            </label>

          </div>

        </section>

        {/* ERROR */}

        {formError && (
          <div
            className="kc-checkout-error"
            role="alert"
          >
            {formError}
          </div>
        )}

        {/* SUBMIT */}

        <button
          type="submit"
          className="kc-btn kc-btn-rose kc-place-order"
          disabled={submitting}
        >
          {submitting
            ? "Creating your secure checkout..."
            : paymentMethod === "mpesa"
              ? "Send M-Pesa prompt"
              : "Place order"}

          {!submitting && (
            <FiArrowRight size={17} />
          )}
        </button>

        <p className="kc-checkout-terms">
          By placing your order, you agree
          to KimCustoms&apos; terms and understand
          that personalized products may not
          be eligible for return once
          production has started.
        </p>

      </div>

      {/* =================================
          ORDER SUMMARY
      ================================= */}

      <aside className="kc-checkout-summary">

        <div className="kc-checkout-summary-inner">

          <span className="kc-eyebrow">
            Your order
          </span>

          <h2>
            {itemCount}{" "}
            {itemCount === 1
              ? "item"
              : "items"}
          </h2>

          <div className="kc-checkout-products">

            {items.map((item) => (
              <div
                key={item.id}
                className="kc-checkout-product"
              >
                <div>
                  <strong>
                    {item.product.name}
                  </strong>

                  <span>
                    Qty {item.quantity}
                  </span>
                </div>

                <strong>
                  KSh{" "}
                  {(
                    item.product.price *
                    item.quantity
                  ).toLocaleString(
                    "en-KE"
                  )}
                </strong>
              </div>
            ))}

          </div>

          <div className="kc-summary-divider" />

          <div className="kc-summary-row">
            <span>
              Subtotal
            </span>

            <strong>
              KSh{" "}
              {subtotal.toLocaleString(
                "en-KE"
              )}
            </strong>
          </div>

          <div className="kc-summary-row">
            <span>
              Delivery
            </span>

            <span className="kc-summary-muted">
              Calculated before payment
            </span>
          </div>

          <div className="kc-summary-divider" />

          <div className="kc-summary-total">
            <span>
              Total
            </span>

            <strong>
              KSh{" "}
              {subtotal.toLocaleString(
                "en-KE"
              )}
            </strong>
          </div>

        </div>

      </aside>

    </form>
  );
}
