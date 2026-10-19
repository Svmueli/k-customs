"use client";

import Image from "next/image";
import Link from "next/link";

import {
  FiArrowRight,
  FiMinus,
  FiPlus,
  FiTrash2,
} from "react-icons/fi";

import { useCart } from "../context/CartContext";

export default function CartPageContent() {
  const {
    items,
    itemCount,
    subtotal,
    updateQuantity,
    removeFromCart,
  } = useCart();

  /* --------------------------------
     Empty cart
  -------------------------------- */

  if (items.length === 0) {
    return (
      <div className="kc-empty-cart">
        <div className="kc-empty-cart-mark">
          ✦
        </div>

        <span className="kc-eyebrow">
          Nothing here yet
        </span>

        <h2>
          Your bag is empty
        </h2>

        <p>
          Your next keepsake is waiting
          to be created.
        </p>

        <Link
          href="/#shop"
          className="kc-btn kc-btn-rose"
        >
          Explore keepsakes
          <FiArrowRight size={17} />
        </Link>
      </div>
    );
  }

  return (
    <div className="kc-cart-layout">

      {/* =================================
          CART ITEMS
      ================================= */}

      <section
        className="kc-cart-items"
        aria-label="Shopping cart items"
      >
        <div className="kc-cart-items-header">
          <h2>
            Your items
          </h2>

          <span>
            {itemCount}{" "}
            {itemCount === 1
              ? "item"
              : "items"}
          </span>
        </div>

        <div className="kc-cart-list">
          {items.map((item) => {
            const itemTotal =
              item.product.price *
              item.quantity;

            /*
             * We support the common image
             * property names while our
             * catalogue is still evolving.
             */
            const productImage =
              (
                item.product as typeof item.product & {
                  image?: string;
                  imageUrl?: string;
                }
              ).image ??
              (
                item.product as typeof item.product & {
                  image?: string;
                  imageUrl?: string;
                }
              ).imageUrl;

            return (
              <article
                key={item.id}
                className="kc-cart-item"
              >
                {/* Product image */}

                <div className="kc-cart-item-image">
                  {productImage ? (
                    <Image
                      src={productImage}
                      alt={
                        item.product.name
                      }
                      fill
                      sizes="(max-width: 767px) 110px, 180px"
                    />
                  ) : (
                    <div className="kc-cart-image-placeholder">
                      ✦
                    </div>
                  )}
                </div>

                {/* Product information */}

                <div className="kc-cart-item-info">
                  <div className="kc-cart-item-top">
                    <div>
                      <span className="kc-cart-item-category">
                        Keepsake
                      </span>

                      <h3>
                        {item.product.name}
                      </h3>
                    </div>

                    <button
                      type="button"
                      className="kc-cart-remove"
                      onClick={() =>
                        removeFromCart(
                          item.id
                        )
                      }
                      aria-label={`Remove ${item.product.name} from cart`}
                    >
                      <FiTrash2
                        size={17}
                      />
                    </button>
                  </div>

                  {/* Personalization */}

                  {item.personalization && (
                    <div className="kc-cart-personalization">
                      <span>
                        Personalization
                      </span>

                      <p>
                        {item.personalization}
                      </p>
                    </div>
                  )}

                  {/* Uploaded image */}

                  {item.imageName && (
                    <div className="kc-cart-upload">
                      <span>
                        Photo
                      </span>

                      <p>
                        {item.imageName}
                      </p>
                    </div>
                  )}

                  {/* Price + quantity */}

                  <div className="kc-cart-item-bottom">
                    <div className="kc-cart-quantity">
                      <button
                        type="button"
                        onClick={() =>
                          updateQuantity(
                            item.id,
                            item.quantity - 1
                          )
                        }
                        aria-label="Decrease quantity"
                      >
                        <FiMinus
                          size={14}
                        />
                      </button>

                      <span
                        aria-live="polite"
                      >
                        {item.quantity}
                      </span>

                      <button
                        type="button"
                        onClick={() =>
                          updateQuantity(
                            item.id,
                            item.quantity + 1
                          )
                        }
                        aria-label="Increase quantity"
                      >
                        <FiPlus
                          size={14}
                        />
                      </button>
                    </div>

                    <div className="kc-cart-item-price">
                      <span>
                        KSh{" "}
                        {item.product.price.toLocaleString(
                          "en-KE"
                        )}{" "}
                        each
                      </span>

                      <strong>
                        KSh{" "}
                        {itemTotal.toLocaleString(
                          "en-KE"
                        )}
                      </strong>
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      {/* =================================
          ORDER SUMMARY
      ================================= */}

      <aside className="kc-cart-summary">
        <div className="kc-cart-summary-inner">
          <span className="kc-eyebrow">
            Order summary
          </span>

          <h2>
            Almost yours.
          </h2>

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
              Calculated at checkout
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

          <Link
            href="/checkout"
            className="kc-btn kc-btn-rose kc-checkout-button"
          >
            Proceed to checkout
            <FiArrowRight size={17} />
          </Link>

          <p className="kc-summary-note">
            You&apos;ll review your delivery
            details and payment method
            before placing the order.
          </p>
        </div>
      </aside>
    </div>
  );
}
