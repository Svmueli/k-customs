import ProductCard from "./ProductCard";
import type { Product } from "@/features/products/data/products";


interface ProductGridProps {
  products: Product[];
}

export default function ProductGrid({
  products,
}: ProductGridProps) {
  if (products.length === 0) {
    return (
      <div className="kc-products-empty">
        <h3>Nothing here yet.</h3>

        <p>
          Try another filter or explore all of our keepsakes.
        </p>
      </div>
    );
  }

  return (
    <div className="kc-product-grid">
      {products.map((product) => (
        <ProductCard
          key={product.id}
          product={product}
        />
      ))}
    </div>
  );
}
