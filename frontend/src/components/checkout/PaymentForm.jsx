import { useState } from 'react';

export default function PaymentForm({ onSubmit, onBack, processing }) {
  const [formData, setFormData] = useState({
    cardNumber: '',
    cardName: '',
    expiry: '',
    cvv: '',
  });
  const [errors, setErrors] = useState({});

  const handleChange = (e) => {
    let { name, value } = e.target;
    
    // Format card number with spaces
    if (name === 'cardNumber') {
      value = value.replace(/\s/g, '').replace(/(\d{4})/g, '$1 ').trim();
      value = value.substring(0, 19);
    }
    
    // Format expiry as MM/YY
    if (name === 'expiry') {
      value = value.replace(/\D/g, '');
      if (value.length >= 2) {
        value = value.substring(0, 2) + '/' + value.substring(2, 4);
      }
    }
    
    // Limit CVV to 4 digits
    if (name === 'cvv') {
      value = value.replace(/\D/g, '').substring(0, 4);
    }
    
    setFormData(prev => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const validate = () => {
    const newErrors = {};
    const cardNum = formData.cardNumber.replace(/\s/g, '');
    
    if (!cardNum || cardNum.length < 15) {
      newErrors.cardNumber = 'Valid card number is required';
    }
    if (!formData.cardName) {
      newErrors.cardName = 'Name on card is required';
    }
    if (!formData.expiry || formData.expiry.length < 5) {
      newErrors.expiry = 'Valid expiry date is required';
    }
    if (!formData.cvv || formData.cvv.length < 3) {
      newErrors.cvv = 'Valid CVV is required';
    }
    return newErrors;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const newErrors = validate();
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    onSubmit({
      cardNumber: formData.cardNumber.replace(/\s/g, ''),
      cardName: formData.cardName,
      expiry: formData.expiry,
      cvv: formData.cvv,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="payment-form" data-testid="payment-form">
      <h2>Payment Information</h2>
      
      <div className="form-group">
        <label htmlFor="cardNumber">Card Number</label>
        <input
          type="text"
          id="cardNumber"
          name="cardNumber"
          value={formData.cardNumber}
          onChange={handleChange}
          placeholder="1234 5678 9012 3456"
          data-testid="card-number"
          className={errors.cardNumber ? 'error' : ''}
          disabled={processing}
        />
        {errors.cardNumber && <span className="error-text">{errors.cardNumber}</span>}
      </div>

      <div className="form-group">
        <label htmlFor="cardName">Name on Card</label>
        <input
          type="text"
          id="cardName"
          name="cardName"
          value={formData.cardName}
          onChange={handleChange}
          placeholder="John Doe"
          data-testid="card-name"
          className={errors.cardName ? 'error' : ''}
          disabled={processing}
        />
        {errors.cardName && <span className="error-text">{errors.cardName}</span>}
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="expiry">Expiry Date</label>
          <input
            type="text"
            id="expiry"
            name="expiry"
            value={formData.expiry}
            onChange={handleChange}
            placeholder="MM/YY"
            data-testid="card-expiry"
            className={errors.expiry ? 'error' : ''}
            disabled={processing}
          />
          {errors.expiry && <span className="error-text">{errors.expiry}</span>}
        </div>
        
        <div className="form-group">
          <label htmlFor="cvv">CVV</label>
          <input
            type="text"
            id="cvv"
            name="cvv"
            value={formData.cvv}
            onChange={handleChange}
            placeholder="123"
            data-testid="card-cvv"
            className={errors.cvv ? 'error' : ''}
            disabled={processing}
          />
          {errors.cvv && <span className="error-text">{errors.cvv}</span>}
        </div>
      </div>

      <div className="payment-actions">
        <button 
          type="button" 
          className="btn-secondary"
          onClick={onBack}
          disabled={processing}
          data-testid="back-to-shipping"
        >
          Back
        </button>
        <button 
          type="submit" 
          className="btn-primary btn-lg"
          disabled={processing}
          data-testid="place-order"
        >
          {processing ? 'Processing...' : 'Place Order'}
        </button>
      </div>
    </form>
  );
}
