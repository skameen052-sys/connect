import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { User, CreditCard, Mail, Phone, Lock, Eye, EyeOff, ArrowRight, Loader2, CheckCircle2 } from 'lucide-react';
import BrandLogo from '../../components/common/BrandLogo';
import { authService } from '../../services/authService';
import '../../styles/auth.css';

export default function EmployeeRegister() {
  const navigate = useNavigate();
  // All fields initialize completely empty
  const [formData, setFormData] = useState({
    fullName: '',
    employeeId: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
  });

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState(false);

  const validate = () => {
    const newErrors = {};

    if (!formData.fullName.trim()) {
      newErrors.fullName = 'Please enter your full name.';
    }

    if (!formData.employeeId.trim()) {
      newErrors.employeeId = 'Please enter your employee ID.';
    } else if (!formData.employeeId.trim().startsWith('AFI')) {
      newErrors.employeeId = 'Employee ID must start with AFI.';
    }

    if (!formData.email.trim()) {
      newErrors.email = 'Please enter your company email address.';
    } else if (!/^[a-zA-Z0-9_.+-]+@arshithgroup\.com$/i.test(formData.email.trim())) {
      newErrors.email = 'Please use your company email ending with @arshithgroup.com.';
    }

    const phoneDigits = formData.phone.replace(/\D/g, '');
    if (!formData.phone.trim() || phoneDigits.length < 10 || phoneDigits.length > 15) {
      newErrors.phone = 'Please enter a valid phone number.';
    }

    if (!formData.password) {
      newErrors.password = 'Please enter your password.';
    } else if (formData.password.length < 8) {
      newErrors.password = 'Password must contain at least 8 characters.';
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Confirm your password';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleFieldChange = (field, value) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));

    if (errors[field] || errors.form) {
      setErrors((prev) => {
        const nextErrors = { ...prev };
        delete nextErrors[field];
        const remainingFieldKeys = Object.keys(nextErrors).filter((k) => k !== 'form');
        if (remainingFieldKeys.length === 0) {
          delete nextErrors.form;
        }
        return nextErrors;
      });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isLoading) return;
    if (!validate()) return;

    setIsLoading(true);
    try {
      await authService.register(formData);
      setIsLoading(false);
      setSuccessMsg(true);
    } catch (err) {
      setIsLoading(false);
      const fieldErrors = err.errors || {};
      const newErrors = {};

      if (fieldErrors.fullName || fieldErrors.full_name) {
        newErrors.fullName = fieldErrors.fullName || fieldErrors.full_name;
      }
      if (fieldErrors.employee_id || fieldErrors.employeeId) {
        newErrors.employeeId = fieldErrors.employee_id || fieldErrors.employeeId;
      }
      if (fieldErrors.email) {
        newErrors.email = fieldErrors.email;
      }
      if (fieldErrors.phone) {
        newErrors.phone = fieldErrors.phone;
      }
      if (fieldErrors.password) {
        newErrors.password = fieldErrors.password;
      }
      if (fieldErrors.confirmPassword || fieldErrors.confirm_password) {
        newErrors.confirmPassword = fieldErrors.confirmPassword || fieldErrors.confirm_password;
      }

      // Check for any other field errors
      Object.keys(fieldErrors).forEach((key) => {
        if (!['fullName', 'full_name', 'employee_id', 'employeeId', 'email', 'phone', 'password', 'confirmPassword', 'confirm_password'].includes(key)) {
          newErrors[key] = fieldErrors[key];
        }
      });

      // Only display top-level banner if there are no field-specific errors, or if server error occurred
      const hasSpecificFieldErrors = Object.keys(newErrors).length > 0;
      if (!hasSpecificFieldErrors || !err.status || err.status >= 500) {
        newErrors.form = err.message || err.detail || "We couldn't complete your registration right now. Please try again later.";
      }

      setErrors(newErrors);
    }
  };


  return (
    <div className="auth-page-wrapper register-theme">
      <div className="register-bg-accent" />
      
      <div className="auth-container register-container animate-fade-in">
        {/* Top Brand Logo with Tagline */}
        <div className="auth-header" style={{ marginBottom: '6px' }}>
          <BrandLogo size="compact" showTagline={true} />
        </div>

        <h1
          style={{
            fontSize: '1.25rem',
            fontWeight: '700',
            color: '#0b3d2b',
            marginBottom: '10px',
            textAlign: 'center'
          }}
        >
          Register Here
        </h1>

        {/* Registration Card */}
        <div className="auth-card" style={{ padding: '18px 22px' }}>
          {successMsg ? (
            <div style={{ textAlign: 'center', padding: '24px 16px' }}>
              <CheckCircle2 size={46} color="#10b981" style={{ margin: '0 auto 12px auto' }} />
              <h2 style={{ fontSize: '1.15rem', color: '#0b3d2b', marginBottom: '8px', fontWeight: '700' }}>
                Registration Submitted!
              </h2>
              <p style={{ fontSize: '0.875rem', color: '#334155', lineHeight: 1.6, marginBottom: '20px' }}>
                Your registration request is awaiting admin approval.
              </p>
              <button
                type="button"
                className="btn-primary-purple"
                onClick={() => navigate('/login')}
                style={{ width: '100%', padding: '10px' }}
              >
                Back to Login
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate>
              {errors.form && (
                <div
                  style={{
                    backgroundColor: '#fef2f2',
                    border: '1px solid #fecaca',
                    color: '#b91c1c',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    fontSize: '0.825rem',
                    marginBottom: '14px',
                    textAlign: 'center',
                  }}
                >
                  {errors.form}
                </div>
              )}
              <div className="register-form-grid">
                {/* Employee Name */}
                <div className="form-group">
                  <div className="input-wrapper">
                    <span className="input-icon-left">
                      <User size={16} />
                    </span>
                    <input
                      type="text"
                      className={`form-input-register ${errors.fullName ? 'form-input-error' : ''}`}
                      placeholder="Employee Name"
                      value={formData.fullName}
                      onChange={(e) => handleFieldChange('fullName', e.target.value)}
                      disabled={isLoading}
                    />
                  </div>
                  {errors.fullName && <span className="input-error-msg">{errors.fullName}</span>}
                </div>

                {/* Employee ID */}
                <div className="form-group">
                  <div className="input-wrapper">
                    <span className="input-icon-left">
                      <CreditCard size={16} />
                    </span>
                    <input
                      type="text"
                      className={`form-input-register ${errors.employeeId ? 'form-input-error' : ''}`}
                      placeholder="Employee ID No. (e.g. AFI-001)"
                      value={formData.employeeId}
                      onChange={(e) => handleFieldChange('employeeId', e.target.value)}
                      disabled={isLoading}
                    />
                  </div>
                  {errors.employeeId && <span className="input-error-msg">{errors.employeeId}</span>}
                </div>

                {/* Official Email */}
                <div className="form-group">
                  <div className="input-wrapper">
                    <span className="input-icon-left">
                      <Mail size={16} />
                    </span>
                    <input
                      type="email"
                      className={`form-input-register ${errors.email ? 'form-input-error' : ''}`}
                      placeholder="example@arshithgroup.com"
                      value={formData.email}
                      onChange={(e) => handleFieldChange('email', e.target.value)}
                      disabled={isLoading}
                    />
                  </div>
                  {errors.email && <span className="input-error-msg">{errors.email}</span>}
                </div>

                {/* Phone Number */}
                <div className="form-group">
                  <div className="input-wrapper">
                    <span className="input-icon-left">
                      <Phone size={16} />
                    </span>
                    <input
                      type="tel"
                      className={`form-input-register ${errors.phone ? 'form-input-error' : ''}`}
                      placeholder="Phone Number"
                      value={formData.phone}
                      onChange={(e) => handleFieldChange('phone', e.target.value)}
                      disabled={isLoading}
                    />
                  </div>
                  {errors.phone && <span className="input-error-msg">{errors.phone}</span>}
                </div>

                {/* Password */}
                <div className="form-group">
                  <div className="input-wrapper">
                    <span className="input-icon-left">
                      <Lock size={16} />
                    </span>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      className={`form-input-register ${errors.password ? 'form-input-error' : ''}`}
                      placeholder="Password"
                      value={formData.password}
                      onChange={(e) => handleFieldChange('password', e.target.value)}
                      disabled={isLoading}
                    />
                    <button
                      type="button"
                      className="input-icon-right"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label="Toggle password visibility"
                      tabIndex={-1}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {errors.password && <span className="input-error-msg">{errors.password}</span>}
                </div>

                {/* Confirm Password */}
                <div className="form-group">
                  <div className="input-wrapper">
                    <span className="input-icon-left">
                      <Lock size={16} />
                    </span>
                    <input
                      type={showConfirmPassword ? 'text' : 'password'}
                      className={`form-input-register ${errors.confirmPassword ? 'form-input-error' : ''}`}
                      placeholder="Confirm Password"
                      value={formData.confirmPassword}
                      onChange={(e) => handleFieldChange('confirmPassword', e.target.value)}
                      disabled={isLoading}
                    />
                    <button
                      type="button"
                      className="input-icon-right"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      aria-label="Toggle confirm password visibility"
                      tabIndex={-1}
                    >
                      {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {errors.confirmPassword && <span className="input-error-msg">{errors.confirmPassword}</span>}
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                className="btn-green-register"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    <span>Registering...</span>
                  </>
                ) : (
                  <>
                    <span>Register</span>
                    <ArrowRight size={16} />
                  </>
                )}
              </button>
            </form>
          )}
        </div>

        {/* Footer Navigation */}
        <footer className="auth-footer" style={{ marginTop: '10px' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color: '#0b3d2b', fontWeight: '700' }}>
            Login
          </Link>
        </footer>
      </div>
    </div>
  );
}
