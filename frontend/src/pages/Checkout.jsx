import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useFlags } from 'launchdarkly-react-client-sdk';
import { LDObserve } from '@launchdarkly/observability';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import ShippingForm from '../components/checkout/ShippingForm';
import PaymentForm from '../components/checkout/PaymentForm';

export default function Checkout() {
  const [step, setStep] = useState(1);
  const [shippingData, setShippingData] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);

  const { cartItems, cartTotal, clearCart } = useCart();
  const { user } = useAuth();
  const flags = useFlags();
  const layoutVariant = flags['product-card-layout'] || 'standard';
  const promoVariant = flags['promo-banner'] || 'none';
  const navigate = useNavigate();

  // Funnel: record checkout_started exactly once when the page mounts with
  // a non-empty cart. Also record cart_size as a histogram for distribution.
  const startedRef = useRef(false);
  useEffect(() => {
    if (startedRef.current) return;
    if (cartItems.length === 0) return;
    startedRef.current = true;

    const itemCount = cartItems.reduce((n, i) => n + (i.quantity || 1), 0);

    const variantAttrs = {
      layout_variant: layoutVariant,
      promo_variant: promoVariant,
    };

    LDObserve.recordCount({
      name: 'app.checkout.started_total',
      value: 1,
      attributes: variantAttrs,
    });
    LDObserve.recordHistogram({
      name: 'app.cart.size',
      value: itemCount,
      attributes: variantAttrs,
    });
    LDObserve.recordHistogram({
      name: 'app.cart.value_usd',
      value: Number(cartTotal.toFixed(2)),
      attributes: variantAttrs,
    });
  }, [cartItems, cartTotal, layoutVariant, promoVariant]);

  const handleShippingSubmit = (data) => {
    setShippingData(data);
    setStep(2);
  };

  const handlePaymentSubmit = async (paymentData) => {
    setProcessing(true);
    setError(null);
    
    try {
      const orderData = {
        user: user || { key: 'guest', email: shippingData.email },
        items: cartItems.map(item => ({
          id: item.id,
          quantity: item.quantity,
          price: item.price,
        })),
        shipping: shippingData,
        payment: {
          cardLast4: paymentData.cardNumber.slice(-4),
        },
        total: cartTotal * 1.08,
      };

      const result = await api.checkout(orderData.user, orderData.items, {
        layout_variant: layoutVariant,
        promo_variant: promoVariant,
      });
      
      if (result.success) {
        clearCart();
        navigate('/order-confirmation', { 
          state: { 
            orderId: result.data.order_id,
            total: orderData.total,
          } 
        });
      } else {
        setError(result.error || 'Checkout failed. Please try again.');
      }
    } catch (err) {
      console.error('Checkout error:', err);
      setError('An error occurred during checkout. Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  if (cartItems.length === 0) {
    navigate('/cart');
    return null;
  }

  return (
    <div className="checkout-page" data-testid="checkout-page">
      <h1>Checkout</h1>
      
      <div className="checkout-progress">
        <div className={`progress-step ${step >= 1 ? 'active' : ''}`}>
          <span className="step-number">1</span>
          <span className="step-label">Shipping</span>
        </div>
        <div className="progress-line" />
        <div className={`progress-step ${step >= 2 ? 'active' : ''}`}>
          <span className="step-number">2</span>
          <span className="step-label">Payment</span>
        </div>
      </div>

      {error && (
        <div className="checkout-error" data-testid="checkout-error">
          {error}
        </div>
      )}

      <div className="checkout-content">
        <div className="checkout-form">
          {step === 1 && (
            <ShippingForm 
              onSubmit={handleShippingSubmit}
              initialData={shippingData}
            />
          )}
          
          {step === 2 && (
            <PaymentForm 
              onSubmit={handlePaymentSubmit}
              onBack={() => setStep(1)}
              processing={processing}
            />
          )}
        </div>

        <div className="checkout-summary">
          <h2>Order Summary</h2>
          <div className="summary-items">
            {cartItems.map(item => (
              <div key={item.id} className="summary-item">
                <span>{item.name} x {item.quantity}</span>
                <span>${(item.price * item.quantity).toFixed(2)}</span>
              </div>
            ))}
          </div>
          <div className="summary-row">
            <span>Subtotal</span>
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
            <span>${(cartTotal * 1.08).toFixed(2)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
