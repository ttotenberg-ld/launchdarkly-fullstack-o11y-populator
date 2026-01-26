import { Link } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import CartItem from '../components/cart/CartItem';

export default function Cart() {
  const { cartItems, cartTotal, clearCart } = useCart();

  if (cartItems.length === 0) {
    return (
      <div className="cart-page" data-testid="cart-page">
        <div className="empty-cart" data-testid="empty-cart">
          <h1>Your Cart is Empty</h1>
          <p>Looks like you haven't added any items to your cart yet.</p>
          <Link to="/products" className="btn-primary" data-testid="continue-shopping">
            Continue Shopping
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="cart-page" data-testid="cart-page">
      <div className="cart-header">
        <h1>Shopping Cart</h1>
        <button 
          className="btn-secondary btn-sm"
          onClick={clearCart}
          data-testid="clear-cart"
        >
          Clear Cart
        </button>
      </div>

      <div className="cart-content">
        <div className="cart-items" data-testid="cart-items">
          {cartItems.map(item => (
            <CartItem key={item.id} item={item} />
          ))}
        </div>

        <div className="cart-summary" data-testid="cart-summary">
          <h2>Order Summary</h2>
          
          <div className="summary-row">
            <span>Subtotal ({cartItems.length} items)</span>
            <span>${cartTotal.toFixed(2)}</span>
          </div>
          
          <div className="summary-row">
            <span>Shipping</span>
            <span>Free</span>
          </div>
          
          <div className="summary-row">
            <span>Tax</span>
            <span>${(cartTotal * 0.08).toFixed(2)}</span>
          </div>
          
          <div className="summary-total">
            <span>Total</span>
            <span data-testid="cart-total">${(cartTotal * 1.08).toFixed(2)}</span>
          </div>

          <Link 
            to="/checkout" 
            className="btn-primary btn-lg btn-full"
            data-testid="checkout-button"
          >
            Proceed to Checkout
          </Link>
          
          <Link to="/products" className="continue-shopping-link">
            Continue Shopping
          </Link>
        </div>
      </div>
    </div>
  );
}
