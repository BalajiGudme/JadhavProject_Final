
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import StudentForm from './StudentForm';
import Webcam from 'react-webcam';

// Set base URL for API
const API_BASE_URL = window.API_BASE_URL || "http://localhost:8000";

// Token utility functions
const getAuthToken = () => {
  const token = 
    localStorage.getItem('access') || 
    localStorage.getItem('authToken') ||
    sessionStorage.getItem('access') ||
    sessionStorage.getItem('authToken');
  return token;
};

const setAuthToken = (token, useLocalStorage = true) => {
  if (useLocalStorage) {
    localStorage.setItem('access', token);
  } else {
    sessionStorage.setItem('access', token);
  }
};

const getRefreshToken = () => {
  return localStorage.getItem('refresh') || sessionStorage.getItem('refresh');
};

const clearTokens = () => {
  localStorage.removeItem('access');
  localStorage.removeItem('refresh');
  localStorage.removeItem('authToken');
  sessionStorage.removeItem('access');
  sessionStorage.removeItem('refresh');
  sessionStorage.removeItem('authToken');
};

const refreshAuthToken = async () => {
  try {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      console.log('No refresh token available');
      return null;
    }

    const response = await axios.post(`${API_BASE_URL}/api/token/refresh/`, {
      refresh: refreshToken
    });

    if (response.data.access) {
      setAuthToken(response.data.access);
      console.log('Token refreshed successfully');
      return response.data.access;
    }
  } catch (error) {
    console.error('Token refresh failed:', error);
    clearTokens();
  }
  return null;
};

const ArchitectureResponsesView = () => {
  const { architectureId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [apiResponse, setApiResponse] = useState(null);
  const [showUnusedTokens, setShowUnusedTokens] = useState(true);
  const [contextMenu, setContextMenu] = useState({ show: false, x: 0, y: 0, token: null, type: null });
  const [editingToken, setEditingToken] = useState(null);
  const [editFormData, setEditFormData] = useState({});
  const [isEditing, setIsEditing] = useState(false);
  const [editFormFields, setEditFormFields] = useState([]);
  const [editLoading, setEditLoading] = useState(false);
  const [showStudentForm, setShowStudentForm] = useState(false);
  const [selectedToken, setSelectedToken] = useState(null);
  const [sendingToAdmin, setSendingToAdmin] = useState(false);
  const [sendStatus, setSendStatus] = useState(null);

  // Image editing state
  const [imageSrc, setImageSrc] = useState(null);
  const [webcamActive, setWebcamActive] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [lastMousePos, setLastMousePos] = useState({ x: 0, y: 0 });
  const [editingImageField, setEditingImageField] = useState(null);
  
  // Refs
  const imgRef = useRef(null);
  const webcamRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    let isMounted = true;
    
    const token = getAuthToken();
    console.log('Component mounted. Token exists:', !!token);
    
    if (!token) {
      if (isMounted) {
        setError('Please log in to access this page');
        setLoading(false);
        setTimeout(() => navigate('/login'), 3000);
      }
      return;
    }
    
    if (architectureId) {
      fetchArchitectureResponses(isMounted);
    }
    
    return () => {
      isMounted = false;
    };
  }, [architectureId]);

  // Close context menu when clicking outside
  useEffect(() => {
    const handleClickOutside = () => {
      if (contextMenu.show) {
        setContextMenu({ show: false, x: 0, y: 0, token: null, type: null });
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  }, [contextMenu]);

  const fetchArchitectureResponses = async (isMounted = true) => {
    try {
      if (isMounted) setLoading(true);
      
      const token = getAuthToken();
      
      if (!token) {
        if (isMounted) {
          setError('No authentication token found. Please log in again.');
          setLoading(false);
        }
        return;
      }
      
      const requestConfig = {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        timeout: 10000
      };

      const response = await axios.get(
        `${API_BASE_URL}/api/architecture/${architectureId}/responses/`,
        requestConfig
      );
      
      if (isMounted) {
        setApiResponse(response.data);
        setData(response.data);
        setError(null);
      }
    } catch (err) {
      console.error('API Error:', err.response?.status, err.response?.data);
      
      if (isMounted) {
        if (err.response?.status === 401) {
          const newToken = await refreshAuthToken();
          if (newToken) {
            fetchArchitectureResponses(isMounted);
            return;
          } else {
            setError('Your session has expired. Please log in again.');
            setTimeout(() => navigate('/login'), 3000);
          }
        } else if (err.response) {
          setError(`Server error: ${err.response.status} - ${err.response.data?.detail || err.response.data?.error || 'Unknown server error'}`);
        } else if (err.request) {
          setError('Cannot connect to server. Please check if the server is running.');
        } else {
          setError(`Request error: ${err.message}`);
        }
      }
    } finally {
      if (isMounted) setLoading(false);
    }
  };

  // Rest of your existing functions (sendToAdmin, goBack, handleSubmitForm, etc.)
  const sendToAdmin = async () => {
    try {
      setSendingToAdmin(true);
      setSendStatus(null);
      
      const token = getAuthToken();
      if (!token) {
        setSendStatus({ type: 'error', message: 'No authentication token found' });
        return;
      }
      
      const requestConfig = {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        timeout: 15000,
        withCredentials: true
      };
      
      const response = await axios.post(
        `${API_BASE_URL}/api/customsentoadmin/${architectureId}/`,
        {},
        requestConfig
      );
      
      setSendStatus({ 
        type: 'success', 
        message: response.data.message || 'Data sent to admin successfully!' 
      });
      
      setTimeout(() => {
        setSendStatus(null);
      }, 5000);
      
    } catch (err) {
      console.error('Error sending to admin:', err);
      
      let errorMessage = 'Failed to send data to admin';
      let showUnusedTokens = false;
      
      if (err.response?.status === 401) {
        const newToken = await refreshAuthToken();
        if (newToken) {
          sendToAdmin();
          return;
        } else {
          errorMessage = 'Your session has expired. Please log in again.';
        }
      } else if (err.response?.status === 403) {
        errorMessage = err.response.data?.details || err.response.data?.message || 'Access denied. You can only submit your own data.';
      } else if (err.response?.status === 400) {
        errorMessage = 'Please complete all token submissions before sending to admin.';
        setShowUnusedTokens(true);
        showUnusedTokens = true;
      } else if (err.response?.data) {
        if (err.response.data.message) {
          errorMessage = err.response.data.message;
        } else if (err.response.data.detail) {
          errorMessage = err.response.data.detail;
        }
      } else if (err.request) {
        errorMessage = 'Cannot connect to server. Please check if the server is running.';
      } else {
        errorMessage = `Request error: ${err.message}`;
      }
      
      setSendStatus({ 
        type: 'error', 
        message: errorMessage,
        showUnusedTokens: showUnusedTokens 
      });
      
      setTimeout(() => {
        setSendStatus(null);
      }, 8000);
    } finally {
      setSendingToAdmin(false);
    }
  };

  const goBack = () => {
    navigate('//architecture');
  };

  const goBack1 = () => {
    navigate('/architecture');
  };

  const handleEditToken = async (token) => {
    try {
      setEditLoading(true);
      setEditingToken(token);
      
      const authToken = getAuthToken();
      const requestConfig = {
        headers: { 
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      };
      
      const response = await axios.get(
        `${API_BASE_URL}/api/token/${token}/edit/`,
        requestConfig
      );
      
      console.log('Edit token response:', response.data);
      
      if (response.data) {
        setEditFormFields(response.data.available_fields || []);
        
        const formData = {};
        if (response.data.responses) {
          response.data.responses.forEach(response => {
            const fieldKey = `field_${response.field_id}`;
            if (response.field_type === 'checkbox') {
              formData[fieldKey] = response.value === true || response.value === 'true' || response.value === 1;
            } else if (response.field_type === 'number') {
              formData[fieldKey] = response.value !== null ? String(response.value) : '';
            } else {
              formData[fieldKey] = response.value !== null ? String(response.value) : '';
            }
          });
        }
        
        setEditFormData(formData);
        setIsEditing(true);
      }
      
    } catch (err) {
      console.error('Error fetching token data for editing:', err);
      if (err.response?.status === 401) {
        const newToken = await refreshAuthToken();
        if (newToken) {
          handleEditToken(token);
          return;
        }
      }
      alert('Failed to load token data for editing');
    } finally {
      setEditLoading(false);
    }
  };

  const handleSubmitForm = (token) => {
    setSelectedToken(token);
    setShowStudentForm(true);
  };

  const handleStudentFormClose = () => {
    setShowStudentForm(false);
    setSelectedToken(null);
    fetchArchitectureResponses();
  };

  // Image editing functions
  const handleMouseDown = (e) => {
    if (!imageSrc) return;
    e.preventDefault();
    setIsDragging(true);
    setLastMousePos({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e) => {
    if (!isDragging || !imageSrc) return;
    
    const deltaX = e.clientX - lastMousePos.x;
    const deltaY = e.clientY - lastMousePos.y;
    
    setPosition(prev => ({
      x: prev.x + deltaX,
      y: prev.y + deltaY
    }));
    
    setLastMousePos({ x: e.clientX, y: e.clientY });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleTouchStart = (e) => {
    if (!imageSrc) return;
    e.preventDefault();
    setIsDragging(true);
    const touch = e.touches[0];
    setLastMousePos({ x: touch.clientX, y: touch.clientY });
  };

  const handleTouchMove = (e) => {
    if (!isDragging || !imageSrc) return;
    e.preventDefault();
    
    const touch = e.touches[0];
    const deltaX = touch.clientX - lastMousePos.x;
    const deltaY = touch.clientY - lastMousePos.y;
    
    setPosition(prev => ({
      x: prev.x + deltaX,
      y: prev.y + deltaY
    }));
    
    setLastMousePos({ x: touch.clientX, y: touch.clientY });
  };

  const handleTouchEnd = () => {
    setIsDragging(false);
  };

  const handleWheel = useCallback((e) => {
    if (!imageSrc) return;
    
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.01 : 0.01;
    const newZoom = Math.min(Math.max(0.5, zoom + delta), 3);
    setZoom(newZoom);
  }, [imageSrc, zoom]);

  const [lastTouchDistance, setLastTouchDistance] = useState(null);

  const handleTouchStartPinch = useCallback((e) => {
    if (e.touches.length === 2) {
      e.preventDefault();
      const touch1 = e.touches[0];
      const touch2 = e.touches[1];
      const distance = Math.hypot(
        touch2.clientX - touch1.clientX,
        touch2.clientY - touch1.clientY
      );
      setLastTouchDistance(distance);
    }
  }, []);

  const handleTouchMovePinch = useCallback((e) => {
    if (e.touches.length === 2 && lastTouchDistance !== null) {
      e.preventDefault();
      const touch1 = e.touches[0];
      const touch2 = e.touches[1];
      const distance = Math.hypot(
        touch2.clientX - touch1.clientX,
        touch2.clientY - touch1.clientY
      );
      
      const zoomFactor = distance / lastTouchDistance;
      const newZoom = Math.min(Math.max(0.5, zoom * zoomFactor), 3);
      setZoom(newZoom);
      setLastTouchDistance(distance);
    }
  }, [lastTouchDistance, zoom]);

  const handleTouchEndPinch = useCallback(() => {
    setLastTouchDistance(null);
  }, []);

  // Add event listeners for wheel and touch zoom
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !imageSrc) return;

    container.addEventListener('wheel', handleWheel, { passive: false });
    container.addEventListener('touchstart', handleTouchStartPinch, { passive: false });
    container.addEventListener('touchmove', handleTouchMovePinch, { passive: false });
    container.addEventListener('touchend', handleTouchEndPinch);

    return () => {
      container.removeEventListener('wheel', handleWheel);
      container.removeEventListener('touchstart', handleTouchStartPinch);
      container.removeEventListener('touchmove', handleTouchMovePinch);
      container.removeEventListener('touchend', handleTouchEndPinch);
    };
  }, [imageSrc, handleWheel, handleTouchStartPinch, handleTouchMovePinch, handleTouchEndPinch]);

  // Crop image to fit the box exactly
  const cropImageToBox = async (field) => {
    if (!imgRef.current || !field.options) return null;

    const canvas = document.createElement('canvas');
    const targetWidth = field.options.width || 300;
    const targetHeight = field.options.height || 300;

    canvas.width = targetWidth;
    canvas.height = targetHeight;
    const ctx = canvas.getContext('2d');

    const container = containerRef.current;
    if (!container) return null;

    const containerRect = container.getBoundingClientRect();
    
    const boxWidth = targetWidth;
    const boxHeight = targetHeight;
    const boxLeft = (containerRect.width - boxWidth) / 2;
    const boxTop = (400 - boxHeight) / 2;

    const scale = zoom;
    const imgElement = imgRef.current;

    const imgXInContainer = position.x;
    const imgYInContainer = position.y;

    const sourceX = (boxLeft - imgXInContainer) / scale;
    const sourceY = (boxTop - imgYInContainer) / scale;
    const sourceWidth = boxWidth / scale;
    const sourceHeight = boxHeight / scale;

    ctx.drawImage(
      imgElement,
      sourceX,
      sourceY,
      sourceWidth,
      sourceHeight,
      0,
      0,
      targetWidth,
      targetHeight
    );

    return new Promise((resolve) => {
      canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.9);
    });
  };

  // Helper function to convert blob to base64
  const blobToBase64 = (blob) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  };

  // Image upload handler for edit modal - FIXED VERSION
  const handleImageUpload = async (field) => {
    try {
      const blob = await cropImageToBox(field);
      if (blob) {
        const base64Image = await blobToBase64(blob);
        const fieldKey = `field_${field.id}`;
        
        console.log('Image processed successfully, updating form data for field:', fieldKey);
        
        setEditFormData(prev => ({
          ...prev,
          [fieldKey]: base64Image
        }));
        
        setImageSrc(null);
        setEditingImageField(null);
        setZoom(1);
        setPosition({ x: 0, y: 0 });
        
        // Show success message
        alert('Image updated successfully! Click "Update Responses" to save all changes.');
      }
    } catch (error) {
      console.error('Error processing image:', error);
      alert('Failed to process image. Please try again.');
    }
  };

  // Render image upload interface
  const renderImageUpload = (field) => {
    const boxWidth = field.options?.width || 300;
    const boxHeight = field.options?.height || 300;

    return (
      <div className="space-y-3 p-4 border rounded-lg bg-gray-50">
        {!imageSrc && !webcamActive && (
          <div className="flex flex-col sm:flex-row gap-3">
            <label className="flex-1 cursor-pointer">
              <span className="bg-blue-500 text-white px-4 py-2 rounded inline-block text-center w-full">
                <i className="fas fa-upload mr-2"></i>Upload Image
              </span>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => {
                  const file = e.target.files[0];
                  if (file) {
                    setImageSrc(URL.createObjectURL(file));
                    setWebcamActive(false);
                    setZoom(1);
                    setPosition({ x: 0, y: 0 });
                  }
                }}
                className="hidden"
              />
            </label>
            <button
              type="button"
              onClick={() => {
                setWebcamActive(true);
                setImageSrc(null);
                setZoom(1);
                setPosition({ x: 0, y: 0 });
              }}
              className="bg-green-500 text-white px-4 py-2 rounded flex-1"
            >
              <i className="fas fa-camera mr-2"></i>Use Webcam
            </button>
          </div>
        )}

        {webcamActive && (
          <div className="space-y-3">
            <Webcam
              ref={webcamRef}
              screenshotFormat="image/jpeg"
              className="rounded border w-full"
              screenshotQuality={0.9}
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  const screenshot = webcamRef.current.getScreenshot();
                  setImageSrc(screenshot);
                  setWebcamActive(false);
                  setZoom(1);
                  setPosition({ x: 0, y: 0 });
                }}
                className="bg-green-600 text-white px-4 py-2 rounded flex-1"
              >
                <i className="fas fa-camera mr-2"></i>Capture
              </button>
              <button
                type="button"
                onClick={() => setWebcamActive(false)}
                className="bg-gray-500 text-white px-4 py-2 rounded flex-1"
              >
                <i className="fas fa-times mr-2"></i>Cancel
              </button>
            </div>
          </div>
        )}

        {imageSrc && (
          <div className="space-y-3">
            <div className="text-center p-2 bg-blue-50 rounded">
              <p className="text-blue-700 font-medium">
                Required Size: {boxWidth} × {boxHeight} pixels
              </p>
              <p className="text-sm text-blue-600">
                • Drag to move image • Mouse wheel to zoom • Pinch to zoom on touch
              </p>
            </div>

            {/* Zoom Controls */}
            <div className="flex items-center justify-between bg-gray-100 p-2 rounded">
              <span className="text-sm font-medium">Zoom:</span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setZoom(Math.max(0.5, zoom - 0.01))}
                  className="bg-gray-200 hover:bg-gray-300 w-8 h-8 rounded flex items-center justify-center"
                  title="Zoom Out (1%)"
                >
                  <i className="fas fa-search-minus"></i>
                </button>
                <span className="text-sm w-16 text-center">{Math.round(zoom * 100)}%</span>
                <button
                  type="button"
                  onClick={() => setZoom(Math.min(3, zoom + 0.01))}
                  className="bg-gray-200 hover:bg-gray-300 w-8 h-8 rounded flex items-center justify-center"
                  title="Zoom In (1%)"
                >
                  <i className="fas fa-search-plus"></i>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setZoom(1);
                    setPosition({ x: 0, y: 0 });
                  }}
                  className="bg-gray-200 hover:bg-gray-300 px-2 py-1 rounded text-sm"
                  title="Reset Zoom"
                >
                  Reset
                </button>
              </div>
            </div>

            {/* Image Container with Fixed Box */}
            <div 
              ref={containerRef}
              className="relative overflow-hidden rounded border-2 border-dashed border-blue-400 bg-gray-100 mx-auto"
              style={{ 
                width: '100%', 
                height: '400px',
                cursor: isDragging ? 'grabbing' : 'grab',
                touchAction: 'none'
              }}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onTouchStart={(e) => {
                handleTouchStart(e);
                handleTouchStartPinch(e);
              }}
              onTouchMove={(e) => {
                handleTouchMove(e);
                handleTouchMovePinch(e);
              }}
              onTouchEnd={(e) => {
                handleTouchEnd(e);
                handleTouchEndPinch(e);
              }}
            >
              {imageSrc && (
                <img
                  ref={imgRef}
                  src={imageSrc}
                  alt="Adjust and crop"
                  className="absolute max-w-none"
                  style={{
                    transform: `scale(${zoom})`,
                    transformOrigin: '0 0',
                    left: `${position.x}px`,
                    top: `${position.y}px`,
                    cursor: isDragging ? 'grabbing' : 'grab'
                  }}
                  onLoad={() => {
                    if (imgRef.current && containerRef.current) {
                      const imgWidth = imgRef.current.naturalWidth;
                      const imgHeight = imgRef.current.naturalHeight;
                      const containerWidth = containerRef.current.clientWidth;
                      const containerHeight = 400;
                      
                      const initialX = (containerWidth - imgWidth) / 2;
                      const initialY = (containerHeight - imgHeight) / 2;
                      
                      setPosition({ x: initialX, y: initialY });
                    }
                  }}
                />
              )}

              {/* Overlay showing the target crop area */}
              <div 
                className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 border-2 border-red-500 bg-transparent pointer-events-none"
                style={{
                  width: `${boxWidth}px`,
                  height: `${boxHeight}px`,
                  boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.3)'
                }}
              >
                <div className="absolute -top-6 left-0 right-0 text-center">
                  <span className="bg-red-500 text-white px-2 py-1 text-sm rounded">
                    {boxWidth} × {boxHeight}
                  </span>
                </div>
              </div>
            </div>

            <div className="text-center text-sm text-gray-600">
              <p>Red box shows exactly what will be saved - Position your image perfectly</p>
            </div>
            
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => handleImageUpload(field)}
                className="bg-blue-600 text-white px-4 py-2 rounded flex-1"
              >
                <i className="fas fa-crop mr-2"></i>Save Image ({boxWidth}×{boxHeight})
              </button>
              <button
                type="button"
                onClick={() => {
                  setImageSrc(null);
                  setZoom(1);
                  setPosition({ x: 0, y: 0 });
                }}
                className="bg-gray-500 text-white px-4 py-2 rounded flex-1"
              >
                <i className="fas fa-times mr-2"></i>Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    );
  };

  // UPDATED: Enhanced handleEditSubmit to properly handle image data
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    
    try {
      setEditLoading(true);
      const authToken = getAuthToken();
      
      // Prepare form data for submission
      const submitData = { ...editFormData };
      
      console.log('Submitting data:', submitData);
      
      // Log image fields to debug
      Object.keys(submitData).forEach(key => {
        if (key.startsWith('field_') && typeof submitData[key] === 'string' && submitData[key].startsWith('data:image')) {
          console.log(`Image field ${key} has data length:`, submitData[key].length);
        }
      });

      const requestConfig = {
        headers: { 
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      };
      
      const response = await axios.put(
        `${API_BASE_URL}/api/token/${editingToken}/edit/`,
        submitData,
        requestConfig
      );
      
      console.log('Update response:', response.data);
      
      alert('Token responses updated successfully!');
      setIsEditing(false);
      setEditingToken(null);
      setEditFormData({});
      setEditFormFields([]);
      fetchArchitectureResponses();
      
    } catch (err) {
      console.error('Error updating token responses:', err);
      console.error('Error details:', err.response?.data);
      
      if (err.response?.status === 401) {
        const newToken = await refreshAuthToken();
        if (newToken) {
          handleEditSubmit(e);
          return;
        }
      }
      
      let errorMessage = 'Failed to update token responses';
      if (err.response?.data) {
        if (err.response.data.detail) {
          errorMessage = err.response.data.detail;
        } else if (err.response.data.error) {
          errorMessage = err.response.data.error;
        } else if (typeof err.response.data === 'string') {
          errorMessage = err.response.data;
        }
      }
      
      alert(errorMessage);
    } finally {
      setEditLoading(false);
    }
  };

  const handleInputChange = (fieldId, value) => {
    setEditFormData(prev => ({
      ...prev,
      [fieldId]: value
    }));
  };

  const handleDeleteToken = async (token) => {
    if (window.confirm(`Are you sure you want to delete token ${token}? This action cannot be undone.`)) {
      try {
        const authToken = getAuthToken();
        const requestConfig = {
          headers: { 
            Authorization: `Bearer ${authToken}`,
            'Content-Type': 'application/json'
          }
        };
        
        await axios.delete(
          `${API_BASE_URL}/api/token/${token}/delete/`,
          requestConfig
        );
        
        fetchArchitectureResponses();
        alert('Token deleted successfully');
      } catch (err) {
        console.error('Delete token error:', err);
        alert('Failed to delete token');
      }
    }
  };

  const handleContextMenu = (e, token, type = 'submitted') => {
    e.preventDefault();
    
    if (type === 'unused') {
      setContextMenu({
        show: true,
        x: e.clientX,
        y: e.clientY,
        token: token,
        type: type
      });
    } else {
      setContextMenu({
        show: true,
        x: e.clientX,
        y: e.clientY,
        token: token,
        type: type
      });
    }
  };

  // Render appropriate input field based on field type
  const renderFieldInput = (field) => {
    const fieldKey = `field_${field.id}`;
    const value = editFormData[fieldKey] || '';
    
    // If we're currently editing an image field, show the image upload interface
    if (editingImageField === field.id) {
      return renderImageUpload(field);
    }
    
    switch (field.type) {
      case 'checkbox':
        return (
          <input
            type="checkbox"
            checked={!!value}
            onChange={(e) => handleInputChange(fieldKey, e.target.checked)}
            className="rounded text-blue-600 focus:ring-blue-500 h-5 w-5"
          />
        );
        
      case 'date':
        return (
          <input
            type="date"
            value={value}
            onChange={(e) => handleInputChange(fieldKey, e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        );
        
      case 'number':
        return (
          <input
            type="number"
            value={value}
            onChange={(e) => handleInputChange(fieldKey, e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            step={field.type === 'integer' ? '1' : 'any'}
          />
        );
        
      case 'dropdown':
        return (
          <select
            value={value}
            onChange={(e) => handleInputChange(fieldKey, e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select an option</option>
            {field.options && field.options.split(',').map((option, index) => (
              <option key={index} value={option.trim()}>
                {option.trim()}
              </option>
            ))}
          </select>
        );
        
      case 'image':
        return (
          <div className="space-y-2">
            {value ? (
              <div className="flex flex-col items-start space-y-3">
                <div className="flex items-center space-x-3">
                  <img 
                    src={value} 
                    alt="Current" 
                    className="w-32 h-32 object-cover rounded border"
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                  />
                  <div className="text-sm text-gray-600">
                    <p className="font-medium">Current Image</p>
                    <p>Size: {field.options?.width || 300}×{field.options?.height || 300}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setEditingImageField(field.id);
                    setImageSrc(null);
                    setWebcamActive(false);
                    setZoom(1);
                    setPosition({ x: 0, y: 0 });
                  }}
                  className="bg-blue-500 text-white px-4 py-2 rounded text-sm hover:bg-blue-600"
                >
                  <i className="fas fa-edit mr-2"></i>Change Image
                </button>
              </div>
            ) : (
              <div className="text-center p-4 border-2 border-dashed border-gray-300 rounded-lg">
                <p className="text-gray-500 mb-3">No image uploaded</p>
                <button
                  type="button"
                  onClick={() => {
                    setEditingImageField(field.id);
                    setImageSrc(null);
                    setWebcamActive(false);
                    setZoom(1);
                    setPosition({ x: 0, y: 0 });
                  }}
                  className="bg-blue-500 text-white px-4 py-2 rounded text-sm hover:bg-blue-600"
                >
                  <i className="fas fa-upload mr-2"></i>Upload Image
                </button>
              </div>
            )}
          </div>
        );
        
      case 'alphanumeric':
        return (
          <input
            type="text"
            value={value}
            onChange={(e) => handleInputChange(fieldKey, e.target.value)}
            pattern="[a-zA-Z0-9]*"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        );
        
      default:
        return (
          <input
            type={field.type === 'email' ? 'email' : 'text'}
            value={value}
            onChange={(e) => handleInputChange(fieldKey, e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        );
    }
  };

  // Render edit modal
  const renderEditModal = () => {
    if (!isEditing) return null;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto">
          <div className="px-6 py-4 border-b">
            <h3 className="text-lg font-semibold text-gray-800">
              Edit Token Responses: {editingToken}
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              Update the field values for this token
            </p>
          </div>
          
          <form onSubmit={handleEditSubmit}>
            <div className="p-6">
              {editLoading ? (
                <div className="flex justify-center items-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                  <p className="ml-3 text-gray-600">Loading form data...</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {editFormFields.map((field) => (
                    <div key={field.id} className="space-y-3 p-4 border border-gray-200 rounded-lg">
                      <label className="block text-sm font-medium text-gray-700">
                        {field.label}
                        {field.required && <span className="text-red-500 ml-1">*</span>}
                        <span className="ml-2 text-xs text-gray-500 capitalize">({field.type})</span>
                      </label>
                      
                      {renderFieldInput(field)}
                      
                      {field.placeholder && (
                        <p className="text-xs text-gray-500">Placeholder: {field.placeholder}</p>
                      )}
                      
                      {field.options && (
                        <p className="text-xs text-gray-500">Options: {typeof field.options === 'string' ? field.options : JSON.stringify(field.options)}</p>
                      )}
                      
                      <div className="flex justify-between text-xs">
                        <span className={`px-2 py-1 rounded ${field.required ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'}`}>
                          {field.required ? 'Required' : 'Optional'}
                        </span>
                        <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded">
                          Order: {field.order}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-between items-center">
              <div className="text-sm text-gray-600">
                Fields: {editFormFields.length} | 
                Required: {editFormFields.filter(f => f.required).length}
              </div>
              <div className="flex space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setIsEditing(false);
                    setEditingToken(null);
                    setEditFormData({});
                    setEditFormFields([]);
                    setEditingImageField(null);
                    setImageSrc(null);
                    setWebcamActive(false);
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                  disabled={editLoading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:bg-blue-300"
                  disabled={editLoading}
                >
                  {editLoading ? 'Updating...' : 'Update Responses'}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    );
  };

  // Rest of your existing functions (groupResponsesByToken, formatValue, getAllTokens, etc.)
  const groupResponsesByToken = () => {
    if (!data || !data.responses) return {};

    const grouped = {};
    data.responses.forEach(response => {
      const token = response.token || 'not-submitted';
      if (!grouped[token]) {
        grouped[token] = {
          token: token,
          responses: {},
          submissionId: response.submission_id,
          architectureName: response.architecture_name,
          timestamp: response.timestamp
        };
      }
      grouped[token].responses[response.field_label] = response;
    });

    return grouped;
  };

  const formatValue = (value, fieldType) => {
    if (value === null || value === undefined || value === '') return '-';
    
    if (fieldType === 'checkbox') {
      return value ? 'Yes' : 'No';
    }
    
    if (fieldType === 'date' && value) {
      return new Date(value).toLocaleDateString();
    }
    
    if (fieldType === 'image' && value) {
      if (value.startsWith('http') || value.startsWith('/') || value.startsWith('data:')) {
        return (
          <div className="flex items-center">
            <img 
              src={value} 
              alt="Uploaded" 
              className="w-16 h-16 object-cover rounded"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
            <span className="ml-2 text-sm text-gray-600">View Image</span>
          </div>
        );
      }
      return 'Image uploaded';
    }

    return String(value);
  };

  const getAllTokens = () => {
    if (!data) return [];
    
    const submittedTokens = data.responses 
      ? [...new Set(data.responses.map(response => response.token).filter(Boolean))]
      : [];
    
    const allTokens = data.tokens || [];
    const unusedTokens = allTokens.filter(token => !submittedTokens.includes(token));
    
    return {
      submitted: submittedTokens,
      unused: unusedTokens,
      all: allTokens
    };
  };

  // Manual retry without any pre-validation
  const manualRetry = () => {
    console.log('Manual retry - token exists:', !!getAuthToken());
    fetchArchitectureResponses();
  };

  // ... (rest of your existing JSX return statement remains the same)
  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <button
          onClick={goBack}
          className="flex items-center text-blue-500 hover:text-blue-700 mb-6"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Architectures
        </button>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          <p className="ml-4 text-gray-600">Loading architecture responses...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <button
          onClick={goBack}
          className="flex items-center text-blue-500 hover:text-blue-700 mb-6"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Architectures
        </button>
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <p className="text-sm text-red-700 mt-1">{error}</p>
              <div className="mt-3 space-x-2">
                <button
                  onClick={manualRetry}
                  className="px-4 py-2 bg-red-100 text-red-700 rounded-md text-sm hover:bg-red-200"
                >
                  Retry
                </button>
                <button
                  onClick={() => {
                    console.log('Current token:', getAuthToken());
                    console.log('Token exists:', !!getAuthToken());
                  }}
                  className="px-4 py-2 bg-blue-100 text-blue-700 rounded-md text-sm hover:bg-blue-200"
                >
                  Debug Token
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!data || (data.token_count === 0 && (!data.responses || data.responses.length === 0))) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <button
          onClick={goBack}
          className="flex items-center text-blue-500 hover:text-blue-700 mb-6"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Architectures
        </button>

        <div className="bg-white rounded-lg shadow-sm border mb-6">
          <div className="px-6 py-4 border-b">
            <h2 className="text-xl font-semibold text-gray-800">
              Architecture Responses: {data?.architecture_name || 'Unknown Architecture'}
            </h2>
          </div>
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
          <h3 className="text-sm font-medium text-yellow-800">No Data Available</h3>
          <p className="text-sm text-yellow-700 mt-1">
            This architecture doesn't have any tokens or responses yet.
          </p>
        </div>
      </div>
    );
  }

  if (showStudentForm) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <button
          onClick={handleStudentFormClose}
          className="flex items-center text-blue-500 hover:text-blue-700 mb-6"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Architecture Responses
        </button>
        
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            Submit Form for Token: {selectedToken}
          </h2>
          <StudentForm 
            preFilledToken={selectedToken}
            onClose={handleStudentFormClose}
          />
        </div>
      </div>
    );
  }

  const groupedResponses = groupResponsesByToken();
  const tokens = getAllTokens();
  
  const allFieldLabels = [...new Set(data.responses
    .filter(response => response.field_label)
    .map(response => response.field_label))];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Edit Modal */}
      {renderEditModal()}

      {/* Context Menu */}
      {contextMenu.show && (
        <div 
          className="fixed bg-white shadow-lg rounded-md py-2 z-50 border border-gray-200"
          style={{ top: contextMenu.y, left: contextMenu.x }}
        >
          {contextMenu.type === 'submitted' && (
            <button
              onClick={() => {
                handleEditToken(contextMenu.token);
                setContextMenu({ show: false, x: 0, y: 0, token: null, type: null });
              }}
              className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Edit
            </button>
          )}
          <button
            onClick={() => {
              handleDeleteToken(contextMenu.token);
              setContextMenu({ show: false, x: 0, y: 0, token: null, type: null });
            }}
            className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-100 flex items-center"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Delete
          </button>
        </div>
      )}

      {/* Back Button */}
      <button
        onClick={goBack1}
        className="flex items-center text-blue-500 hover:text-blue-700 mb-6"
      >
        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        Back to Architectures
      </button>

      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border mb-6">
        <div className="px-6 py-4 border-b flex justify-between items-center">
          <div>
            <h2 className="text-xl font-semibold text-gray-800">
              Architecture Responses: {data.architecture_name}
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              Architecture ID: {architectureId}
              {data && ` • Total Tokens: ${tokens.all.length} • Submitted: ${tokens.submitted.length} • Unused: ${tokens.unused.length}`}
            </p>
          </div>
          
          {/* Send to Admin Button */}
          <div className="flex flex-col items-end space-y-2">
            <div className="text-right">
              <button
                onClick={sendToAdmin}
                disabled={sendingToAdmin}
                className={`px-4 py-2 text-sm font-medium rounded-md flex items-center ${
                  sendingToAdmin 
                    ? 'bg-gray-400 text-gray-700 cursor-not-allowed' 
                    : 'bg-green-600 text-white hover:bg-green-700'
                }`}
              >
                {sendingToAdmin ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Sending...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                    Send for ID Card Processing
                  </>
                )}
              </button>
              
              {/* Help text */}
              <div className="text-xs text-gray-500 mt-1 max-w-xs">
                {tokens.unused.length > 0 
                  ? `${tokens.unused.length} unused tokens remaining - complete all to send` 
                  : 'Send all completed data for ID card processing'
                }
              </div>
            </div>
            
            {/* Status Message */}
            {sendStatus && (
              <div className={`text-xs px-3 py-2 rounded max-w-md ${
                sendStatus.type === 'success' 
                  ? 'bg-green-100 text-green-800 border border-green-200' 
                  : 'bg-red-100 text-red-800 border border-red-200'
              }`}>
                <div className="font-medium mb-1">
                  {sendStatus.type === 'success' ? 'Success!' : 'Unable to Send'}
                </div>
                <div>{sendStatus.message}</div>
                {sendStatus.type === 'error' && sendStatus.showUnusedTokens && (
                  <div className="mt-2 text-red-700 font-medium flex items-center">
                    <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                    Please check unused tokens below
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
        
        <div className="px-6 py-3 bg-blue-50 border-b">
          <div className="flex justify-between items-center">
            <button
              onClick={() => fetchArchitectureResponses()}
              className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200 flex items-center"
            >
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
            
            <div className="text-sm text-blue-700">
              Click "Send for ID Card Processing" to submit all completed data to administrators
            </div>
          </div>
        </div>
      </div>

      {/* Responses Table */}
      <div className="bg-white rounded-lg shadow-sm border mb-6">
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-medium text-gray-800">
            Submitted Token Responses ({tokens.submitted.length})
          </h3>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Sr. No
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Token
                </th>
                {allFieldLabels.map((fieldLabel, index) => (
                  <th key={index} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {fieldLabel}
                  </th>
                ))}
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {tokens.submitted.map((token, index) => (
                <tr key={token} onContextMenu={(e) => handleContextMenu(e, token, 'submitted')} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {index + 1}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {token}
                  </td>
                  {allFieldLabels.map((fieldLabel, fieldIndex) => {
                    const response = groupedResponses[token]?.responses[fieldLabel];
                    return (
                      <td key={fieldIndex} className="px-6 py-4 text-sm text-gray-900">
                        {response ? formatValue(response.value, response.field_type) : '-'}
                      </td>
                    );
                  })}
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button
                      onClick={() => handleEditToken(token)}
                      className="text-blue-600 hover:text-blue-900 mr-3 flex items-center"
                      title="Edit token responses"
                    >
                      <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                      Edit
                    </button>
                    <button
                      onClick={() => handleDeleteToken(token)}
                      className="text-red-600 hover:text-red-900 flex items-center"
                      title="Delete token"
                    >
                      <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Unused Tokens Section */}
      {(showUnusedTokens || tokens.unused.length > 0) && (
        <div className="bg-white rounded-lg shadow-sm border mb-6">
          <div className="px-6 py-4 border-b flex justify-between items-center bg-yellow-50">
            <div>
              <h3 className="text-lg font-medium text-yellow-800">
                Unused Tokens ({tokens.unused.length})
              </h3>
              <p className="text-sm text-yellow-600 mt-1">
                Complete these forms to enable ID card processing
              </p>
            </div>
            <button
              onClick={() => setShowUnusedTokens(false)}
              className="text-yellow-600 hover:text-yellow-800"
            >
              Hide
            </button>
          </div>
          
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {tokens.unused.map((token) => (
                <div 
                  key={token} 
                  className="bg-yellow-50 border border-yellow-300 rounded-lg p-4 hover:bg-yellow-100 transition-colors duration-200 cursor-pointer shadow-sm"
                  onClick={() => handleSubmitForm(token)}
                  onContextMenu={(e) => handleContextMenu(e, token, 'unused')}
                  title="Click to submit form for this token. Right-click for delete option."
                >
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <div className="text-lg font-semibold text-yellow-800">{token}</div>
                      <div className="text-sm text-yellow-600">Not Submitted</div>
                    </div>
                    <div className="text-xs text-yellow-700 bg-yellow-200 px-2 py-1 rounded font-medium">
                      Click to Submit
                    </div>
                  </div>
                  <div className="text-xs text-yellow-600 flex items-center">
                    <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Complete this form to proceed with ID card processing
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ArchitectureResponsesView;

