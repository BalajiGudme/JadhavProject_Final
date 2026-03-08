
// export default ArchitectureManager;
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom'; 

const API_BASE_URL = 'http://localhost:8000/api';

// Token management utilities
const getaccess = () => localStorage.getItem('access');
const getrefresh = () => localStorage.getItem('refresh');
const setTokens = (access, refresh) => {
  localStorage.setItem('access', access);
  localStorage.setItem('refresh', refresh);
};
const clearTokens = () => {
  localStorage.removeItem('access');
  localStorage.removeItem('refresh');
};

// Enhanced fetch with token handling
const createAuthFetch = () => {
  const refresh = async () => {
    try {
      const refresh = getrefresh();
      if (!refresh) {
        throw new Error('No refresh token available');
      }

      const response = await fetch(`${API_BASE_URL}/token/refresh/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh }),
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const data = await response.json();
      setTokens(data.access, refresh);
      return data.access;
    } catch (error) {
      console.error('Token refresh failed:', error);
      clearTokens();
      window.location.href = '/login';
      throw error;
    }
  };

  const authFetch = async (url, options = {}) => {
    let access = getaccess();
    
    // Set up headers with authorization
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (access) {
      headers['Authorization'] = `Bearer ${access}`;
    }

    const config = {
      ...options,
      headers,
    };

    let response = await fetch(url, config);

    // If token is expired, try to refresh and retry
    if (response.status === 401 && access) {
      try {
        access = await refresh();
        headers['Authorization'] = `Bearer ${access}`;
        
        // Retry the original request with new token
        response = await fetch(url, {
          ...config,
          headers,
        });
      } catch (error) {
        // Refresh failed, redirect to login
        clearTokens();
        window.location.href = '/login';
        return response;
      }
    }

    return response;
  };

  return authFetch;
};

// QR Code Generation Page Component
const QRCodeGenerationPage = ({ selectedArchitectures, onBack, existingTokens = null }) => {
  const [selectedForm, setSelectedForm] = useState('');
  const [qrCodes, setQrCodes] = useState([]);
  const [forms, setForms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const authFetch = createAuthFetch();

  // Calculate total count from selected architectures
  const totalCount = selectedArchitectures.reduce((total, arch) => {
    return total + (arch.student_count || 0) + (arch.staff_count || 0);
  }, 0);

  // Calculate live available count
  const liveAvailableCount = selectedArchitectures.reduce((total, arch) => {
    return total + (arch.live_student_count || 0) + (arch.live_staff_count || 0);
  }, 0);

  // Load QR.js library
  useEffect(() => {
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/qrious/4.0.2/qrious.min.js';
    script.onload = () => {
      console.log('QR library loaded');
    };
    document.head.appendChild(script);

    return () => {
      document.head.removeChild(script);
    };
  }, []);

  // Fetch published forms
  useEffect(() => {
    const fetchPublishedForms = async () => {
      try {
        setLoading(true);
        const response = await authFetch(`${API_BASE_URL}/forms/`);
        
        if (!response.ok) {
          throw new Error('Failed to fetch forms');
        }

        const data = await response.json();
        const publishedForms = data.filter(form => form.is_published);
        
        setForms(publishedForms);
        setError(null);
      } catch (error) {
        console.error('Error fetching published forms:', error);
        setError('Failed to load forms. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchPublishedForms();
  }, []);

  // Filter existing tokens to only show those for selected architectures
  useEffect(() => {
    if (existingTokens && existingTokens.length > 0) {
      const selectedArchIds = selectedArchitectures.map(arch => arch.id);
      const filteredTokens = existingTokens.filter(token => 
        selectedArchIds.includes(token.backendData.architecture)
      );
      
      setQrCodes(filteredTokens);
      setSuccess(`Loaded ${filteredTokens.length} existing tokens for selected architectures`);
    }
  }, [existingTokens, selectedArchitectures]);

  const generateQRCodes = async () => {
    if (!selectedForm) {
      alert('Please select a form first');
      return;
    }

    setGenerating(true);
    setError(null);
    setSuccess(null);

    try {
      // Prepare the request data for each architecture
      const requests = selectedArchitectures.flatMap(arch => {
        const requestsForArch = [];
        
        // Calculate how many new tokens to generate based on live counts
        const studentTokensNeeded = Math.max(0, (arch.student_count || 0) - (arch.live_student_count || 0));
        const staffTokensNeeded = Math.max(0, (arch.staff_count || 0) - (arch.live_staff_count || 0));
        
        // Create requests for students
        for (let i = 0; i < studentTokensNeeded; i++) {
          requestsForArch.push({
            form_id: parseInt(selectedForm),
            architecture_id: arch.id,
            count: 1, // Generate 1 token per request
            user_type: 'student'
          });
        }
        
        // Create requests for staff
        for (let i = 0; i < staffTokensNeeded; i++) {
          requestsForArch.push({
            form_id: parseInt(selectedForm),
            architecture_id: arch.id,
            count: 1, // Generate 1 token per request
            user_type: 'staff'
          });
        }
        
        return requestsForArch;
      });

      console.log('Prepared requests:', requests);

      // If no tokens needed (all are already available)
      if (requests.length === 0) {
        setSuccess('All tokens are already available. No new tokens needed.');
        setGenerating(false);
        return;
      }

      // Make all API calls
      const responses = await Promise.all(
        requests.map(request => 
          authFetch(`${API_BASE_URL}/form-tokens/generate-multiple/`, {
            method: 'POST',
            body: JSON.stringify(request)
          })
        )
      );

      // Check all responses
      const errors = [];
      const results = [];

      for (const response of responses) {
        if (!response.ok) {
          const errorText = await response.text();
          errors.push(`Server returned ${response.status}: ${errorText}`);
        } else {
          const result = await response.json();
          results.push(result);
        }
      }

      if (errors.length > 0) {
        throw new Error(errors.join('; '));
      }

      // Process all results
      const allTokens = results.flatMap(result => {
        if (Array.isArray(result)) {
          return result;
        } else if (result.success && Array.isArray(result.tokens)) {
          return result.tokens;
        } else {
          return [];
        }
      });

      setSuccess(`Successfully generated ${allTokens.length} tokens`);
      
      // Transform the backend response into QR code data
      const newQrCodes = allTokens.map(token => {
        const redirectUrl = `http://localhost:5173/student`;
        const qrData = {
          formId: token.form,
          formName: token.form_title || 'Unknown Form',
          architectureId: token.architecture,
          architectureName: token.architecture_name || 'Unknown Architecture',
          token: token.token,
          timestamp: token.created_at || new Date().toISOString(),
          id: token.id,
          isValid: token.is_valid,
          isUsed: token.is_used,
          redirectUrl: redirectUrl
        };
        
        return {
          id: token.id,
          token: token.token,
          qrValue: redirectUrl,
          displayData: qrData,
          form: token.form_title || 'Unknown Form',
          architecture: token.architecture_name || 'Unknown',
          userType: token.user_type || 'User',
          backendData: token
        };
      });
      
      setQrCodes(newQrCodes);
      
      // Refresh parent component to update live counts
      if (typeof onBack === 'function') {
        // Trigger a refresh in parent
        setTimeout(() => {
          if (window.refreshArchitectures) {
            window.refreshArchitectures();
          }
        }, 1000);
      }
    } catch (error) {
      console.error('Error generating QR codes:', error);
      setError(error.message || 'Failed to generate QR codes. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  const downloadQRCode = async (qrCode) => {
    try {
      // Create a temporary canvas to generate the QR code
      const canvas = document.createElement('canvas');
      const size = 300;
      canvas.width = size;
      canvas.height = size;
      
      if (window.QRious) {
        const qr = new window.QRious({
          element: canvas,
          value: qrCode.qrValue,
          size: size,
          level: 'M'
        });
        
        // Download the canvas as PNG
        const link = document.createElement('a');
        link.download = `qrcode-${qrCode.token}.png`;
        link.href = canvas.toDataURL();
        link.click();
      } else {
        // Fallback: download as text file with all backend data
        const content = `QR Code Information:
Token: ${qrCode.token}
Form: ${qrCode.form} (ID: ${qrCode.backendData.form})
Architecture: ${qrCode.architecture} (ID: ${qrCode.backendData.architecture})
Status: ${qrCode.backendData.is_valid ? 'Valid' : 'Invalid'} ${qrCode.backendData.is_used ? '(Used)' : '(Unused)'}
Created: ${new Date(qrCode.backendData.created_at).toLocaleString()}
Backend ID: ${qrCode.backendData.id}

QR Data: ${qrCode.qrValue}`;
        
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `qrcode-${qrCode.token}.txt`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error('Error downloading QR code:', error);
      alert('Error downloading QR code. Please try again.');
    }
  };

  const downloadQRCodesPDF = async () => {
    try {
      // Load jsPDF library
      const jsPDFScript = document.createElement('script');
      jsPDFScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
      
      await new Promise((resolve, reject) => {
        jsPDFScript.onload = resolve;
        jsPDFScript.onerror = reject;
        document.head.appendChild(jsPDFScript);
      });

      const { jsPDF } = window.jspdf;
      const pdf = new jsPDF();
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      
      // Grid settings
      const cols = 4; // 4 columns total (2 pairs of Info+QR)
      const rows = 5; // 5 rows
      const itemsPerPage = cols * rows; // 20 items (10 QR codes with their info)
      
      const margin = 15;
      const cellWidth = (pageWidth - (2 * margin)) / cols;
      const qrSize = 30; // QR code size
      const startY = 20;
      const rowHeight = 50; // Height per row
      
      let qrCodeIndex = 0;
      const totalQRCodes = qrCodes.length;
      
      for (let pageStart = 0; pageStart < totalQRCodes; pageStart += (rows * 2)) { // Each row holds 2 QR codes (using 4 columns)
        if (pageStart > 0) {
          pdf.addPage();
        }
        
        // Calculate how many QR codes to show on this page (max 10 per page - 5 rows × 2 QR codes per row)
        const qrCodesForPage = Math.min(10, totalQRCodes - pageStart);
        
        for (let row = 0; row < rows && (row * 2) < qrCodesForPage; row++) {
          for (let pair = 0; pair < 2; pair++) { // 2 pairs per row (Info+QR)
            const currentQrIndex = pageStart + (row * 2) + pair;
            
            // Break if we've processed all QR codes
            if (currentQrIndex >= totalQRCodes) break;
            
            const qrCode = qrCodes[currentQrIndex];
            
            // Calculate column positions for this pair
            // Pair 0 uses columns 0 (Info) and 1 (QR)
            // Pair 1 uses columns 2 (Info) and 3 (QR)
            const infoCol = pair * 2; // 0 for first pair, 2 for second pair
            const qrCol = pair * 2 + 1; // 1 for first pair, 3 for second pair
            
            // Calculate Y position for this row
            const yPos = startY + (row * rowHeight);
            
            // INFORMATION COLUMN
            const infoX = margin + (infoCol * cellWidth);
            
            pdf.setFontSize(8);
            pdf.setFont('helvetica', 'bold');
            
            // Token (with wrapping)
            const tokenLines = pdf.splitTextToSize(`Token: ${qrCode.token}`, cellWidth - 8);
            let textY = yPos + 5;
            
            pdf.text(tokenLines[0], infoX + 2, textY);
            textY += 4;
            
            if (tokenLines.length > 1) {
              pdf.text(tokenLines[1], infoX + 2, textY);
              textY += 4;
            }
            
            pdf.setFont('helvetica', 'normal');
            pdf.setFontSize(7);
            
            // Form
            const formLines = pdf.splitTextToSize(`Form: ${qrCode.form}`, cellWidth - 8);
            pdf.text(formLines[0], infoX + 2, textY);
            textY += 4;
            
            if (formLines.length > 1) {
              pdf.text(formLines[1], infoX + 2, textY);
              textY += 4;
            }
            
            // Architecture
            pdf.text(`Arch: ${qrCode.architecture}`, infoX + 2, textY);
            textY += 4;
            
            // Status
            const status = `${qrCode.backendData.is_valid ? 'Valid' : 'Invalid'} ${qrCode.backendData.is_used ? '(Used)' : '(Unused)'}`;
            const statusLines = pdf.splitTextToSize(`Status: ${status}`, cellWidth - 8);
            pdf.text(statusLines[0], infoX + 2, textY);
            textY += 4;
            
            if (statusLines.length > 1) {
              pdf.text(statusLines[1], infoX + 2, textY);
              textY += 4;
            }
            
            // Created date
            pdf.text(`Created: ${new Date(qrCode.backendData.created_at).toLocaleDateString()}`, infoX + 2, textY);
            
            // QR CODE COLUMN
            if (window.QRious) {
              const qrX = margin + (qrCol * cellWidth);
              
              const canvas = document.createElement('canvas');
              canvas.width = qrSize * 2;
              canvas.height = qrSize * 2;
              
              new window.QRious({
                element: canvas,
                value: qrCode.qrValue,
                size: qrSize * 2,
                level: 'M'
              });
              
              // Center QR code in its column
              const qrXPos = qrX + (cellWidth - qrSize) / 2;
              const qrYPos = yPos + 5;
              
              const qrImage = canvas.toDataURL('image/png');
              pdf.addImage(qrImage, 'PNG', qrXPos, qrYPos, qrSize, qrSize);
              
              // Add small token reference below QR
              pdf.setFontSize(5);
              pdf.setFont('helvetica', 'normal');
              const shortToken = qrCode.token.length > 8 ? 
                qrCode.token.substring(0, 6) + '...' : 
                qrCode.token;
              pdf.text(shortToken, qrXPos, qrYPos + qrSize + 3);
            }
          }
        }
        
        // Add light grid lines to visualize columns and rows (optional)
        pdf.setDrawColor(230, 230, 230);
        pdf.setLineWidth(0.1);
        
        // Draw vertical lines
        for (let col = 0; col <= cols; col++) {
          const xLine = margin + (col * cellWidth);
          pdf.line(xLine, startY - 5, xLine, startY + (rows * rowHeight) - 5);
        }
        
        // Draw horizontal lines
        for (let row = 0; row <= rows; row++) {
          const yLine = startY - 5 + (row * rowHeight);
          pdf.line(margin, yLine, pageWidth - margin, yLine);
        }
        
        // Add page header showing range
        const startNum = pageStart + 1;
        const endNum = Math.min(pageStart + (rows * 2), totalQRCodes);
        pdf.setFontSize(10);
        pdf.setFont('helvetica', 'bold');
        pdf.text(`QR Codes ${startNum} to ${endNum} of ${totalQRCodes}`, margin, startY - 8);
      }
      
      // Add footer with total count
      const totalPages = pdf.internal.getNumberOfPages();
      for (let i = 1; i <= totalPages; i++) {
        pdf.setPage(i);
        pdf.setFontSize(8);
        pdf.text(`Generated: ${new Date().toLocaleString()}`, margin, pageHeight - 10);
      }
      
      // Save PDF
      pdf.save(`qrcodes-${new Date().toISOString().split('T')[0]}.pdf`);
      
    } catch (error) {
      console.error('Error generating PDF:', error);
      alert('Error generating PDF. Downloading as text file instead.');
      downloadAllQRCodes();
    }
  };

  const downloadAllQRCodes = () => {
    // Get architecture and form from first QR code (assuming they're the same for all)
    const architectureName = qrCodes.length > 0 ? qrCodes[0].architecture : 'N/A';
    const formName = qrCodes.length > 0 ? qrCodes[0].form : 'N/A';
    
    // Create header
    const header = `Architecture: ${architectureName}
Form: ${formName}
Generated: ${new Date().toLocaleString()}
${'='.repeat(40)}

Sr.No. | Token
${'-'.repeat(40)}`;
    
    // Add tokens with serial numbers
    const tokensWithSrNo = qrCodes.map((qr, index) => 
      `${String(index + 1).padStart(5)} | ${qr.token}`
    ).join('\n');
    
    // Combine header and tokens
    const content = `${header}\n${tokensWithSrNo}`;
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tokens-${new Date().toISOString().split('T')[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
};

  const SimpleQRDisplay = ({ value, size = 150 }) => {
    const canvasRef = useRef(null);
    
    useEffect(() => {
      if (canvasRef.current && window.QRious) {
        try {
          new window.QRious({
            element: canvasRef.current,
            value: value,
            size: size,
            level: 'M',
            foreground: '#000000',
            background: '#ffffff'
          });
        } catch (error) {
          console.error('Error generating QR code:', error);
          // Fallback display
          const canvas = canvasRef.current;
          const ctx = canvas.getContext('2d');
          ctx.fillStyle = '#f0f0f0';
          ctx.fillRect(0, 0, size, size);
          ctx.fillStyle = '#333';
          ctx.font = '12px Arial';
          ctx.textAlign = 'center';
          ctx.fillText('QR Code', size/2, size/2);
        }
      }
    }, [value, size]);
    
    return <canvas ref={canvasRef} width={size} height={size} className="border" />;
  };

  return (
    <div className="bg-white shadow-md rounded p-4 mt-4">
      <button 
        className="bg-gray-500 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded mb-4"
        onClick={onBack}
      >
        ← Back to Architecture List
      </button>
      
      <h2 className="text-2xl font-semibold mb-4">
        {existingTokens ? 'Existing QR Codes' : 'Generate QR Codes'}
      </h2>
      
      <div className="mb-6 p-4 bg-blue-50 rounded-lg">
        <h3 className="font-medium mb-3 text-lg">Selected Architectures:</h3>
        <div className="space-y-2">
          {selectedArchitectures.map(arch => (
            <div key={arch.id} className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white p-2 rounded gap-2">
              <span className="font-medium">{arch.name}</span>
              <div className="text-sm text-gray-600 flex flex-wrap gap-2">
                {arch.student_count > 0 && (
                  <span className="bg-blue-100 px-2 py-1 rounded">
                    {arch.student_count} students 
                    {arch.live_student_count !== undefined && (
                      <span className={`ml-1 ${arch.live_student_count < arch.student_count ? 'text-red-500' : 'text-green-500'}`}>
                        ({arch.live_student_count} live)
                      </span>
                    )}
                  </span>
                )}
                {arch.staff_count > 0 && (
                  <span className="bg-green-100 px-2 py-1 rounded">
                    {arch.staff_count} staff
                    {arch.live_staff_count !== undefined && (
                      <span className={`ml-1 ${arch.live_staff_count < arch.staff_count ? 'text-red-500' : 'text-green-500'}`}>
                        ({arch.live_staff_count} live)
                      </span>
                    )}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
        {!existingTokens && (
          <div className="mt-3 p-2 bg-yellow-100 rounded">
            <p className="font-semibold text-center">
              Total QR Codes allocated: {totalCount}
              {liveAvailableCount !== totalCount && (
                <span className="block text-sm font-normal mt-1">
                  Live available: {liveAvailableCount} | To generate: {totalCount - liveAvailableCount}
                </span>
              )}
            </p>
          </div>
        )}
      </div>
      
      {!existingTokens && (
        <div className="mb-6">
          <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="formSelect">
            Select a form for QR codes:
          </label>
          {loading ? (
            <div className="text-gray-500 py-4">Loading available forms...</div>
          ) : error ? (
            <div className="text-red-500 mb-2 p-2 bg-red-50 rounded">{error}</div>
          ) : forms.length === 0 ? (
            <div className="text-red-500 p-4 bg-red-50 rounded">
              No published forms available. Please create and publish forms in the form builder first.
            </div>
          ) : (
            <div>
              <select
                id="formSelect"
                className="shadow appearance-none border rounded w-full py-3 px-4 
                         bg-white text-gray-800 leading-tight focus:outline-none focus:shadow-outline focus:border-blue-500"
                value={selectedForm}
                onChange={(e) => setSelectedForm(e.target.value)}
              >
                <option value="" className="text-gray-500">
                  -- Choose a form --
                </option>
                {forms.map((form) => (
                  <option 
                    key={form.id} 
                    value={form.id}
                    className="text-gray-800 font-medium"
                  >
                    {form.title || form.name}
                  </option>
                ))}
              </select>
              <div className="text-sm text-gray-600 mt-2">
                {forms.length} published form{forms.length !== 1 ? 's' : ''} available
              </div>
            </div>
          )}
        </div>
      )}
      
      {!existingTokens && (
        <div className="mb-6">
          <button
            className="bg-green-500 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-lg text-lg disabled:bg-gray-400 disabled:cursor-not-allowed w-full sm:w-auto"
            onClick={generateQRCodes}
            disabled={!selectedForm || forms.length === 0 || generating || liveAvailableCount === totalCount}
            title={liveAvailableCount === totalCount ? "All tokens are already available" : ""}
          >
            {generating ? 'Generating...' : `Generate ${totalCount - liveAvailableCount} QR Codes`}
          </button>
          
          {liveAvailableCount === totalCount && totalCount > 0 && (
            <div className="mt-2 text-green-500">
              All {totalCount} tokens are already available. No generation needed.
            </div>
          )}
          
          {generating && (
            <div className="mt-2 text-blue-500">
              Generating tokens via backend API...
            </div>
          )}
          
          {error && (
            <div className="mt-2 p-2 bg-red-100 text-red-700 rounded">
              Error: {error}
            </div>
          )}
        </div>
      )}
      
      {success && (
        <div className="mt-2 p-2 bg-green-100 text-green-700 rounded mb-6">
          {success}
        </div>
      )}
      
      {qrCodes.length > 0 && (
        <div>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-3">
            <h3 className="text-xl font-semibold">QR Codes ({qrCodes.length})</h3>
            <div className="flex flex-wrap gap-2">
              <button
                className="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded text-sm"
                onClick={downloadQRCodesPDF}
              >
                Download PDF
              </button>
              <button
                className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded text-sm"
                onClick={downloadAllQRCodes}
              >
                Download Data
              </button>
            </div>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {qrCodes.map(qrCode => (
              <div key={qrCode.id} className="border rounded-lg p-4 bg-white shadow-sm hover:shadow-md transition-shadow">
                <div className="text-center mb-3">
                  <SimpleQRDisplay value={qrCode.qrValue} size={150} />
                </div>
                
                <div className="space-y-2 text-sm">
                  <div className="text-center">
                    <span className="font-mono text-sm sm:text-base md:text-lg font-bold bg-gray-100 px-2 py-1 rounded break-all">
                      {qrCode.token}
                    </span>
                  </div>
                  
                  <div className="border-t pt-2">
                    <p><strong>Form:</strong> <span className="break-words">{qrCode.form}</span></p>
                    <p><strong>Architecture:</strong> <span className="break-words">{qrCode.architecture}</span></p>
                    <p><strong>Status:</strong> 
                      <span className={`ml-1 px-2 py-1 rounded text-xs ${
                        qrCode.backendData.is_valid 
                          ? (qrCode.backendData.is_used ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800')
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {qrCode.backendData.is_valid 
                          ? (qrCode.backendData.is_used ? 'Used' : 'Valid') 
                          : 'Invalid'}
                      </span>
                    </p>
                    <p><strong>Created:</strong> {new Date(qrCode.backendData.created_at).toLocaleString()}</p>
                    <p><strong>ID:</strong> <span className="text-xs font-mono break-all">{qrCode.backendData.id}</span></p>
                  </div>
                </div>
                
                <button
                  className="w-full mt-3 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-3 rounded text-sm"
                  onClick={() => downloadQRCode(qrCode)}
                >
                  Download PNG
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Main Architecture Manager Component
const ArchitectureManager = () => {
  const [architectures, setArchitectures] = useState([]);
  const [studentArchitectures, setStudentArchitectures] = useState([]);
  const [staffArchitectures, setStaffArchitectures] = useState([]);
  const [selectedArchitecture, setSelectedArchitecture] = useState(null);
  const [treeView, setTreeView] = useState([]);
  const [view, setView] = useState('students');
  const [formData, setFormData] = useState({
    name: '',
    institution_type: '',
    department_name: '',
    class_name: '',
    division: '',
    student_count: 0,
    staff_count: 0,
    is_active: true,
    parent: null
  });
  const [isEditing, setIsEditing] = useState(false);
  const [selectedRows, setSelectedRows] = useState([]);
  const [showQRPage, setShowQRPage] = useState(false);
  const [selectedArchitectures, setSelectedArchitectures] = useState([]);
  const [existingTokens, setExistingTokens] = useState(null);
  const [previousView, setPreviousView] = useState('students');
  
  // Search states
  const [studentSearchTerm, setStudentSearchTerm] = useState('');
  const [staffSearchTerm, setStaffSearchTerm] = useState('');
  
  // Pagination states for student records
  const [studentCurrentPage, setStudentCurrentPage] = useState(1);
  const [studentRecordsPerPage, setStudentRecordsPerPage] = useState(20);
  
  // Pagination states for staff records
  const [staffCurrentPage, setStaffCurrentPage] = useState(1);
  const [staffRecordsPerPage, setStaffRecordsPerPage] = useState(20);
  
  const [recordsPerPageOptions] = useState([5, 10, 20, 50, 100]);
  
  const navigate = useNavigate();
  const authFetch = createAuthFetch();

  // Institution types
  const INSTITUTION_TYPES = [
    { value: 'College', label: 'College' },
    { value: 'University', label: 'University' },
    { value: 'School', label: 'School' },
    { value: 'Company', label: 'Company' },
    { value: 'Department', label: 'Department' },
    { value: 'Faculty', label: 'Faculty' },
    { value: 'Institute', label: 'Institute' },
    { value: 'Division', label: 'Division' },
    { value: 'Section', label: 'Section' },
    { value: 'Unit', label: 'Unit' }
  ];

  // Check authentication on component mount
  useEffect(() => {
    const checkAuth = () => {
      const token = getaccess();
      if (!token) {
        navigate('/login');
        return false;
      }
      return true;
    };

    if (!checkAuth()) {
      return;
    }
  }, [navigate]);

  // Fetch all architectures with live counts
  const fetchArchitectures = async () => {
    try {
      const [archResponse, tokensResponse] = await Promise.all([
        authFetch(`${API_BASE_URL}/architecture/`),
        authFetch(`${API_BASE_URL}/form-tokens/`)
      ]);
      
      if (!archResponse.ok || !tokensResponse.ok) {
        throw new Error('Failed to fetch data');
      }
      
      const architectures = await archResponse.json();
      const allTokens = await tokensResponse.json();
      
      // Calculate token counts for each architecture
      const architecturesWithTokenData = architectures.map(arch => {
        // Filter tokens for this specific architecture
        const archTokens = allTokens.filter(token => token.architecture === arch.id);
        
        // Calculate token statistics (same logic as ArchitectureResponsesView)
        const submittedTokens = archTokens.filter(token => token.is_used);
        const unusedTokens = archTokens.filter(token => !token.is_used);
        
        return {
          ...arch,
          // Add token data to each architecture
          tokenData: {
            all: archTokens,
            submitted: submittedTokens,
            unused: unusedTokens
          }
        };
      });
      
      setArchitectures(architecturesWithTokenData);
    } catch (error) {
      console.error('Error fetching architectures:', error);
      if (error.message.includes('Authentication')) {
        navigate('/login');
      }
    }
  };

  useEffect(() => {
    fetchArchitectures();
    fetchTree();
    
    // Make fetchArchitectures available globally for QR component to refresh
    window.refreshArchitectures = fetchArchitectures;
    
    return () => {
      delete window.refreshArchitectures;
    };
  }, []);

  // Filter architectures when architectures change
  useEffect(() => {
    const studentArchs = architectures.filter(arch => arch.student_count > 0);
    const staffArchs = architectures.filter(arch => arch.staff_count > 0);
    
    setStudentArchitectures(studentArchs);
    setStaffArchitectures(staffArchs);
    
    // Reset to first page when data changes
    setStudentCurrentPage(1);
    setStaffCurrentPage(1);
  }, [architectures]);

  // Update selected architectures when selectedRows changes
  useEffect(() => {
    const selected = architectures.filter(arch => selectedRows.includes(arch.id));
    setSelectedArchitectures(selected);
  }, [selectedRows, architectures]);

  // Reset to first page when search term changes
  useEffect(() => {
    setStudentCurrentPage(1);
  }, [studentSearchTerm]);

  useEffect(() => {
    setStaffCurrentPage(1);
  }, [staffSearchTerm]);

  const fetchTree = async () => {
    try {
      const response = await authFetch(`${API_BASE_URL}/architecture-tree/`);
      if (!response.ok) {
        throw new Error('Failed to fetch tree');
      }
      const data = await response.json();
      setTreeView(data);
    } catch (error) {
      console.error('Error fetching tree:', error);
    }
  };

  const fetchArchitectureDetails = async (architectureId) => {
    try {
      navigate(`/architecture/${architectureId}/responses`);
    } catch (error) {
      console.error('Error fetching architecture details:', error);
    }
  };

  const fetchArchitectureDetails1 = async (architectureId) => {
    try {
      navigate(`/architecture/${architectureId}/responses`);
    } catch (error) {
      console.error('Error fetching architecture details:', error);
    }
  };

  // Function to fetch existing tokens
  const fetchExistingTokens = async () => {
    try {
      const response = await authFetch(`${API_BASE_URL}/form-tokens/`);
      if (!response.ok) {
        throw new Error('Failed to fetch existing tokens');
      }
      const data = await response.json();
      
      // Transform tokens to QR code format
      return data.map(token => {
        const redirectUrl = `http://localhost:5173/student`;
        return {
          id: token.id,
          token: token.token,
          qrValue: redirectUrl,
          displayData: {
            formId: token.form,
            formName: token.form_title || 'Unknown Form',
            architectureId: token.architecture,
            architectureName: token.architecture_name || 'Unknown Architecture',
            token: token.token,
            timestamp: token.created_at || new Date().toISOString(),
            id: token.id,
            isValid: token.is_valid,
            isUsed: token.is_used,
            redirectUrl: redirectUrl
          },
          form: token.form_title || 'Unknown Form',
          architecture: token.architecture_name || 'Unknown',
          userType: token.user_type || 'User',
          backendData: token  // This contains the architecture ID
        };
      });
    } catch (error) {
      console.error('Error fetching existing tokens:', error);
      return [];
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      const response = await authFetch(`${API_BASE_URL}/architecture/`, {
        method: 'POST',
        body: JSON.stringify(formData)
      });
      
      if (!response.ok) {
        throw new Error('Failed to create architecture');
      }
      
      setFormData({ 
        name: '', 
        institution_type: '', 
        department_name: '', 
        class_name: '', 
        division: '', 
        student_count: 0, 
        staff_count: 0, 
        is_active: true, 
        parent: null 
      });
      fetchArchitectures();
      fetchTree();
      alert('Architecture created successfully!');
      setView(previousView);
    } catch (error) {
      console.error('Error creating architecture:', error);
      alert('Error creating architecture. Please try again.');
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    try {
      const response = await authFetch(
        `${API_BASE_URL}/architecture/${selectedArchitecture.id}/`,
        {
          method: 'PUT',
          body: JSON.stringify(formData)
        }
      );
      
      if (!response.ok) {
        throw new Error('Failed to update architecture');
      }
      
      setIsEditing(false);
      setFormData({ 
        name: '', 
        institution_type: '', 
        department_name: '', 
        class_name: '', 
        division: '', 
        student_count: 0, 
        staff_count: 0, 
        is_active: true, 
        parent: null 
      });
      fetchArchitectures();
      fetchTree();
      setView(previousView);
      alert('Architecture updated successfully!');
    } catch (error) {
      console.error('Error updating architecture:', error);
      alert('Error updating architecture. Please try again.');
    }
  };

 const handleDelete = async (id) => {
  if (window.confirm('Are you sure you want to delete this architecture?')) {
    try {
      console.log(`Attempting to delete architecture ID: ${id}`);
      
      const response = await authFetch(`${API_BASE_URL}/architecture/${id}/delete/`, {
        method: 'DELETE'
      });
      
      console.log('Response status:', response.status);
      
      let responseData;
      try {
        responseData = await response.json();
        console.log('Response data:', responseData);
      } catch (e) {
        console.log('Could not parse response as JSON');
      }
      
      if (!response.ok) {
        const errorMessage = responseData?.error || responseData?.details || `Failed to delete (Status: ${response.status})`;
        throw new Error(errorMessage);
      }
      
      alert(responseData?.message || 'Architecture deleted successfully!');
      
      // Refresh the data
      await fetchArchitectures();
      await fetchTree();
      setView(previousView);
      
    } catch (error) {
      console.error('Error deleting architecture:', error);
      alert(`Error: ${error.message}`);
    }
  }
};

  const handleAddNew = (type) => {
    setSelectedArchitecture(null);
    setFormData({ 
      name: '', 
      institution_type: '', 
      department_name: '', 
      class_name: '', 
      division: '', 
      student_count: type === 'student' ? 1 : 0, 
      staff_count: type === 'staff' ? 1 : 0, 
      is_active: true, 
      parent: null 
    });
    setIsEditing(false);
    setPreviousView(view);
    setView('detail');
  };

  const handleRowSelect = (id) => {
    if (selectedRows.includes(id)) {
      setSelectedRows(selectedRows.filter(rowId => rowId !== id));
    } else {
      setSelectedRows([...selectedRows, id]);
    }
  };

  const handleSelectAll = (architectures) => {
    if (selectedRows.length === architectures.length) {
      setSelectedRows([]);
    } else {
      setSelectedRows(architectures.map(arch => arch.id));
    }
  };

  const handleGenerateQR = async () => {
    if (selectedRows.length === 0) {
      alert('Please select at least one row to generate QR codes');
      return;
    }
    
    try {
      // Fetch all existing tokens first
      const allTokens = await fetchExistingTokens();
      console.log('All tokens:', allTokens);
      
      // Check which selected architectures already have tokens
      const architecturesWithTokens = [];
      const architecturesWithoutTokens = [];
      
      for (const arch of selectedArchitectures) {
        const hasTokens = allTokens.some(token => 
          token.backendData.architecture === arch.id
        );
        console.log(`Arch ${arch.id} (${arch.name}) has tokens:`, hasTokens);
        
        if (hasTokens) {
          architecturesWithTokens.push(arch);
        } else {
          architecturesWithoutTokens.push(arch);
        }
      }
      
      console.log('With tokens:', architecturesWithTokens);
      console.log('Without tokens:', architecturesWithoutTokens);
      
      // If ALL selected architectures already have tokens
      if (architecturesWithoutTokens.length === 0) {
        const shouldViewExisting = window.confirm(
          'All selected architectures already have tokens. ' +
          'Would you like to view the existing tokens instead?'
        );
        
        if (shouldViewExisting) {
          const filteredTokens = allTokens.filter(token => 
            selectedRows.includes(token.backendData.architecture)
          );
          setExistingTokens(filteredTokens);
          setShowQRPage(true);
        }
        return;
      }
      
      // If SOME architectures have tokens, show alert
      if (architecturesWithTokens.length > 0) {
        const archNamesWithTokens = architecturesWithTokens.map(arch => arch.name).join(', ');
        alert(`The following architectures already have tokens and will be excluded: ${archNamesWithTokens}`);
      }
      
      // Update selected rows to only include architectures without tokens
      const newSelectedRows = architecturesWithoutTokens.map(arch => arch.id);
      const newSelectedArchitectures = architecturesWithoutTokens;
      
      console.log('New selected rows:', newSelectedRows);
      console.log('New selected architectures:', newSelectedArchitectures);
      
      setSelectedArchitectures(newSelectedArchitectures);
      setSelectedRows(newSelectedRows);
      
      // Proceed with generation for architectures without tokens
      setExistingTokens(null);
      setShowQRPage(true);
      
    } catch (error) {
      console.error('Error in handleGenerateQR:', error);
      alert('Error checking for existing tokens. Please try again.');
    }
  };

  const handleSingleQRGeneration = async (arch) => {
    // Automatically select this row
    setSelectedRows([arch.id]);
    setSelectedArchitectures([arch]);
    
    try {
      // Fetch all existing tokens
      const allTokens = await fetchExistingTokens();
      
      // Filter tokens for this specific architecture ID
      const archSpecificTokens = allTokens.filter(token => 
        token.backendData.architecture === arch.id
      );
      
      const hasExistingTokens = archSpecificTokens.length > 0;
      
      if (hasExistingTokens) {
        // Only allow viewing existing tokens, not generating new ones
        const shouldViewExisting = window.confirm(
          'Tokens already exist for this architecture. ' +
          'You can only view existing tokens when they already exist. ' +
          'Would you like to view the existing tokens?'
        );
        
        if (shouldViewExisting) {
          setExistingTokens(archSpecificTokens);
          setShowQRPage(true);
        }
        // If user cancels, don't proceed with generation
        return;
      }
      
      // Only generate new tokens if no existing tokens found
      setExistingTokens(null);
      setShowQRPage(true);
    } catch (error) {
      console.error('Error handling QR generation:', error);
      // If there's an error fetching tokens, don't proceed with generation
      // You might want to show an error message to the user instead
      alert('Error checking for existing tokens. Please try again.');
    }
  };

  // Search filter function for student records
  const filteredStudentArchitectures = studentArchitectures.filter(arch => {
    const searchTerm = studentSearchTerm.toLowerCase();
    return (
      arch.id.toString().includes(searchTerm) ||
      (arch.name && arch.name.toLowerCase().includes(searchTerm)) ||
      (arch.institution_type && arch.institution_type.toLowerCase().includes(searchTerm)) ||
      (arch.department_name && arch.department_name.toLowerCase().includes(searchTerm)) ||
      (arch.class_name && arch.class_name.toLowerCase().includes(searchTerm)) ||
      (arch.division && arch.division.toLowerCase().includes(searchTerm))
    );
  });

  // Search filter function for staff records
  const filteredStaffArchitectures = staffArchitectures.filter(arch => {
    const searchTerm = staffSearchTerm.toLowerCase();
    return (
      arch.id.toString().includes(searchTerm) ||
      (arch.name && arch.name.toLowerCase().includes(searchTerm)) ||
      (arch.institution_type && arch.institution_type.toLowerCase().includes(searchTerm)) ||
      (arch.department_name && arch.department_name.toLowerCase().includes(searchTerm))
    );
  });

  // Pagination logic for student records
  const studentIndexOfLastRecord = studentCurrentPage * studentRecordsPerPage;
  const studentIndexOfFirstRecord = studentIndexOfLastRecord - studentRecordsPerPage;
  const studentCurrentRecords = filteredStudentArchitectures.slice(studentIndexOfFirstRecord, studentIndexOfLastRecord);
  const studentTotalPages = Math.ceil(filteredStudentArchitectures.length / studentRecordsPerPage);

  // Pagination logic for staff records
  const staffIndexOfLastRecord = staffCurrentPage * staffRecordsPerPage;
  const staffIndexOfFirstRecord = staffIndexOfLastRecord - staffRecordsPerPage;
  const staffCurrentRecords = filteredStaffArchitectures.slice(staffIndexOfFirstRecord, staffIndexOfLastRecord);
  const staffTotalPages = Math.ceil(filteredStaffArchitectures.length / staffRecordsPerPage);

  // Helper function to render action buttons based on custom_sent_to_admin
  const renderActionButtons = (arch) => {
    // Check for multiple possible values
    if (arch.custm_sent_to_admin === true || arch.custom_sent_to_admin === 1 || arch.custom_sent_to_admin === "1") {
      return (
        <td className="py-3 px-2 sm:px-3 text-center">
          <span className="text-green-600 font-semibold text-xs sm:text-sm">Sent</span>
        </td>
      );
    }
    
    // Normal action buttons when custom_sent_to_admin is falsy
    return (
      <td className="py-3 px-2 sm:px-3 text-center">
        <div className="flex flex-col sm:flex-row items-center justify-center gap-2">
          <button 
            className="text-blue-500 hover:text-blue-700 text-xs sm:text-sm whitespace-nowrap"
            onClick={() => fetchArchitectureDetails1(arch.id)}
          >
            View
          </button>
          <button 
            className="text-red-500 hover:text-red-700 text-xs sm:text-sm whitespace-nowrap"
            onClick={() => handleDelete(arch.id)}
          >
            Delete
          </button>
          <button 
            className="text-purple-500 hover:text-purple-700 text-xs sm:text-sm whitespace-nowrap"
            onClick={() => handleSingleQRGeneration(arch)}
            title="Generate QR Code"
          >
            <span className="flex items-center">
              <span className="mr-1">📋</span>
              <span className="hidden sm:inline">QR</span>
            </span>
          </button>
        </div>
      </td>
    );
  };

  // Add the missing renderTree function
  const renderTree = (nodes) => {
    return (
      <ul className="pl-2 sm:pl-5">
        {nodes.map(node => (
          <li key={node.id} className="my-2">
            <div 
              className={`p-2 sm:p-3 rounded cursor-pointer hover:bg-gray-200 ${
                node.student_count > 0 ? 'bg-blue-100' : 
                node.staff_count > 0 ? 'bg-green-100' : 'bg-gray-100'
              }`}
              onClick={() => fetchArchitectureDetails(node.id)}
            >
              <span className="font-medium text-sm sm:text-base">{node.name}</span>
              {node.institution_type && (
                <span className="ml-2 text-xs sm:text-sm text-blue-600">({node.institution_type})</span>
              )}
              {node.department_name && <p className="text-xs sm:text-sm text-gray-600">Dept: {node.department_name}</p>}
              {node.class_name && <p className="text-xs sm:text-sm text-gray-500">Class: {node.class_name}</p>}
              {node.division && <p className="text-xs sm:text-sm text-gray-500">Division: {node.division}</p>}
              <p className="text-xs sm:text-sm text-gray-500">
                {node.student_count > 0 && `Students: ${node.student_count} `}
                {node.staff_count > 0 && `Staff: ${node.staff_count}`}
              </p>
              {(node.live_student_count !== undefined || node.live_staff_count !== undefined) && (
                <p className="text-xs text-gray-500 mt-1">
                  {node.live_student_count !== undefined && `Live Students: ${node.live_student_count} `}
                  {node.live_staff_count !== undefined && `Live Staff: ${node.live_staff_count}`}
                </p>
              )}
              <div className="flex mt-1 flex-wrap gap-1">
                {node.student_count > 0 && (
                  <span className="text-xs bg-blue-500 text-white px-2 py-1 rounded">
                    Student
                  </span>
                )}
                {node.staff_count > 0 && (
                  <span className="text-xs bg-green-500 text-white px-2 py-1 rounded">
                    Staff
                  </span>
                )}
              </div>
            </div>
            {node.children && node.children.length > 0 && renderTree(node.children)}
          </li>
        ))}
      </ul>
    );
  };

  // Mobile card view for student records
  const StudentMobileCard = ({ arch, index, actualIndex }) => {
    return (
      <div className="border border-gray-200 rounded-lg p-4 mb-3 bg-white shadow-sm">
        <div className="flex justify-between items-start mb-2">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={selectedRows.includes(arch.id)}
              onChange={() => handleRowSelect(arch.id)}
              className="h-4 w-4"
            />
            <span className="font-bold text-blue-600">#{actualIndex}</span>
          </div>
          <div className="flex gap-2">
            <button 
              className="text-blue-500 hover:text-blue-700 text-sm px-2 py-1 bg-blue-50 rounded"
              onClick={() => fetchArchitectureDetails1(arch.id)}
            >
              View
            </button>
            <button 
              className="text-red-500 hover:text-red-700 text-sm px-2 py-1 bg-red-50 rounded"
              onClick={() => handleDelete(arch.id)}
            >
              Delete
            </button>
            <button 
              className="text-purple-500 hover:text-purple-700 text-sm px-2 py-1 bg-purple-50 rounded"
              onClick={() => handleSingleQRGeneration(arch)}
              title="Generate QR Code"
            >
              📋
            </button>
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span className="text-gray-500">Arch ID:</span>
            <span className="ml-1 font-mono">{arch.id}</span>
          </div>
          <div>
            <span className="text-gray-500">Name:</span>
            <span className="ml-1 font-medium truncate block" title={arch.name}>{arch.name}</span>
          </div>
          <div>
            <span className="text-gray-500">Type:</span>
            <span className="ml-1">{arch.institution_type || '-'}</span>
          </div>
          <div>
            <span className="text-gray-500">Dept:</span>
            <span className="ml-1 truncate block" title={arch.department_name || '-'}>{arch.department_name || '-'}</span>
          </div>
          {arch.class_name && (
            <div>
              <span className="text-gray-500">Class:</span>
              <span className="ml-1">{arch.class_name}</span>
            </div>
          )}
          {arch.division && (
            <div>
              <span className="text-gray-500">Div:</span>
              <span className="ml-1">{arch.division}</span>
            </div>
          )}
          <div>
            <span className="text-gray-500">Students:</span>
            <span className={`ml-1 font-semibold ${
              arch.tokenData && arch.tokenData.all.length > 0
                ? arch.tokenData.all.length < arch.student_count
                  ? 'text-orange-600'
                  : 'text-green-600'
                : 'text-green-600'
            }`}>
              {arch.tokenData && arch.tokenData.all.length > 0 
                ? arch.tokenData.all.length 
                : arch.student_count}
            </span>
          </div>
        </div>
        
        {arch.custm_sent_to_admin === true || arch.custom_sent_to_admin === 1 || arch.custom_sent_to_admin === "1" ? (
          <div className="mt-2 text-center">
            <span className="text-green-600 font-semibold bg-green-50 px-3 py-1 rounded-full text-sm">Sent</span>
          </div>
        ) : null}
      </div>
    );
  };

  // Mobile card view for staff records
  const StaffMobileCard = ({ arch, index, actualIndex }) => {
    return (
      <div className="border border-gray-200 rounded-lg p-4 mb-3 bg-white shadow-sm">
        <div className="flex justify-between items-start mb-2">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={selectedRows.includes(arch.id)}
              onChange={() => handleRowSelect(arch.id)}
              className="h-4 w-4"
            />
            <span className="font-bold text-green-600">#{actualIndex}</span>
          </div>
          <div className="flex gap-2">
            <button 
              className="text-blue-500 hover:text-blue-700 text-sm px-2 py-1 bg-blue-50 rounded"
              onClick={() => fetchArchitectureDetails1(arch.id)}
            >
              View
            </button>
            <button 
              className="text-red-500 hover:text-red-700 text-sm px-2 py-1 bg-red-50 rounded"
              onClick={() => handleDelete(arch.id)}
            >
              Delete
            </button>
            <button 
              className="text-purple-500 hover:text-purple-700 text-sm px-2 py-1 bg-purple-50 rounded"
              onClick={() => handleSingleQRGeneration(arch)}
              title="Generate QR Code"
            >
              📋
            </button>
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span className="text-gray-500">Arch ID:</span>
            <span className="ml-1 font-mono">{arch.id}</span>
          </div>
          <div>
            <span className="text-gray-500">Name:</span>
            <span className="ml-1 font-medium truncate block" title={arch.name}>{arch.name}</span>
          </div>
          <div>
            <span className="text-gray-500">Type:</span>
            <span className="ml-1">{arch.institution_type || '-'}</span>
          </div>
          <div>
            <span className="text-gray-500">Dept:</span>
            <span className="ml-1 truncate block" title={arch.department_name || '-'}>{arch.department_name || '-'}</span>
          </div>
          <div>
            <span className="text-gray-500">Staff:</span>
            <span className={`ml-1 font-semibold ${
              arch.tokenData && arch.tokenData.all.length > 0
                ? arch.tokenData.all.length < arch.staff_count
                  ? 'text-orange-600'
                  : 'text-green-600'
                : 'text-green-600'
            }`}>
              {arch.tokenData && arch.tokenData.all.length > 0 
                ? arch.tokenData.all.length 
                : arch.staff_count}
            </span>
          </div>
        </div>
        
        {arch.custm_sent_to_admin === true || arch.custom_sent_to_admin === 1 || arch.custom_sent_to_admin === "1" ? (
          <div className="mt-2 text-center">
            <span className="text-green-600 font-semibold bg-green-50 px-3 py-1 rounded-full text-sm">Sent</span>
          </div>
        ) : null}
      </div>
    );
  };

  // Pagination component for student table
  const StudentPagination = () => {
    if (filteredStudentArchitectures.length === 0) return null;
    
    return (
      <div className="px-4 sm:px-6 py-4 border-t flex flex-col sm:flex-row justify-between items-center gap-4">
        <div className="flex flex-col sm:flex-row items-center gap-2 text-sm">
          <span className="text-gray-700">
            Showing {studentIndexOfFirstRecord + 1} to {Math.min(studentIndexOfLastRecord, filteredStudentArchitectures.length)} of {filteredStudentArchitectures.length} records
          </span>
          <select
            value={studentRecordsPerPage}
            onChange={(e) => {
              setStudentRecordsPerPage(Number(e.target.value));
              setStudentCurrentPage(1);
            }}
            className="px-2 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-full sm:w-auto"
          >
            {recordsPerPageOptions.map(option => (
              <option key={option} value={option}>
                {option} per page
              </option>
            ))}
          </select>
        </div>
        
        <div className="flex flex-wrap items-center justify-center gap-1 sm:gap-2">
          <button
            onClick={() => setStudentCurrentPage(1)}
            disabled={studentCurrentPage === 1}
            className={`px-2 sm:px-3 py-1 rounded-md text-xs sm:text-sm transition-colors ${
              studentCurrentPage === 1
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            First
          </button>
          <button
            onClick={() => setStudentCurrentPage(prev => Math.max(prev - 1, 1))}
            disabled={studentCurrentPage === 1}
            className={`px-2 sm:px-3 py-1 rounded-md text-xs sm:text-sm transition-colors ${
              studentCurrentPage === 1
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Prev
          </button>
          
          <span className="px-2 sm:px-3 py-1 text-xs sm:text-sm font-medium">
            Page {studentCurrentPage} of {studentTotalPages || 1}
          </span>
          
          <button
            onClick={() => setStudentCurrentPage(prev => Math.min(prev + 1, studentTotalPages))}
            disabled={studentCurrentPage === studentTotalPages || studentTotalPages === 0}
            className={`px-2 sm:px-3 py-1 rounded-md text-xs sm:text-sm transition-colors ${
              studentCurrentPage === studentTotalPages || studentTotalPages === 0
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Next
          </button>
          <button
            onClick={() => setStudentCurrentPage(studentTotalPages)}
            disabled={studentCurrentPage === studentTotalPages || studentTotalPages === 0}
            className={`px-2 sm:px-3 py-1 rounded-md text-xs sm:text-sm transition-colors ${
              studentCurrentPage === studentTotalPages || studentTotalPages === 0
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Last
          </button>
        </div>
      </div>
    );
  };

  // Pagination component for staff table
  const StaffPagination = () => {
    if (filteredStaffArchitectures.length === 0) return null;
    
    return (
      <div className="px-4 sm:px-6 py-4 border-t flex flex-col sm:flex-row justify-between items-center gap-4">
        <div className="flex flex-col sm:flex-row items-center gap-2 text-sm">
          <span className="text-gray-700">
            Showing {staffIndexOfFirstRecord + 1} to {Math.min(staffIndexOfLastRecord, filteredStaffArchitectures.length)} of {filteredStaffArchitectures.length} records
          </span>
          <select
            value={staffRecordsPerPage}
            onChange={(e) => {
              setStaffRecordsPerPage(Number(e.target.value));
              setStaffCurrentPage(1);
            }}
            className="px-2 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-full sm:w-auto"
          >
            {recordsPerPageOptions.map(option => (
              <option key={option} value={option}>
                {option} per page
              </option>
            ))}
          </select>
        </div>
        
        <div className="flex flex-wrap items-center justify-center gap-1 sm:gap-2">
          <button
            onClick={() => setStaffCurrentPage(1)}
            disabled={staffCurrentPage === 1}
            className={`px-2 sm:px-3 py-1 rounded-md text-xs sm:text-sm transition-colors ${
              staffCurrentPage === 1
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            First
          </button>
          <button
            onClick={() => setStaffCurrentPage(prev => Math.max(prev - 1, 1))}
            disabled={staffCurrentPage === 1}
            className={`px-2 sm:px-3 py-1 rounded-md text-xs sm:text-sm transition-colors ${
              staffCurrentPage === 1
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Prev
          </button>
          
          <span className="px-2 sm:px-3 py-1 text-xs sm:text-sm font-medium">
            Page {staffCurrentPage} of {staffTotalPages || 1}
          </span>
          
          <button
            onClick={() => setStaffCurrentPage(prev => Math.min(prev + 1, staffTotalPages))}
            disabled={staffCurrentPage === staffTotalPages || staffTotalPages === 0}
            className={`px-2 sm:px-3 py-1 rounded-md text-xs sm:text-sm transition-colors ${
              staffCurrentPage === staffTotalPages || staffTotalPages === 0
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Next
          </button>
          <button
            onClick={() => setStaffCurrentPage(staffTotalPages)}
            disabled={staffCurrentPage === staffTotalPages || staffTotalPages === 0}
            className={`px-2 sm:px-3 py-1 rounded-md text-xs sm:text-sm transition-colors ${
              staffCurrentPage === staffTotalPages || staffTotalPages === 0
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Last
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="container mx-auto px-2 sm:px-4 py-4 sm:py-8 mt-16 sm:mt-20">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 sm:mb-6 gap-3">
        <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-blue-800">Architecture Management</h1>
      </div>
      
      <div className="flex flex-wrap gap-2 mb-4 sm:mb-6">
        <button 
          className={`px-3 py-2 text-xs sm:text-sm md:text-base rounded ${
            view === 'students' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700'
          }`}
          onClick={() => setView('students')}
        >
          Student Records
        </button>
        <button 
          className={`px-3 py-2 text-xs sm:text-sm md:text-base rounded ${
            view === 'staff' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700'
          }`}
          onClick={() => setView('staff')}
        >
          Staff Records
        </button>
        <button 
          className={`px-3 py-2 text-xs sm:text-sm md:text-base rounded ${
            view === 'tree' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700'
          }`}
          onClick={() => setView('tree')}
        >
          Tree View
        </button>
        
        {/* Add New Dropdown */}
        {/* Add New Dropdown */}
<div className="relative ml-auto group">
  <button className="px-3 py-2 text-xs sm:text-sm md:text-base bg-green-500 text-white rounded flex items-center gap-1">
    Add New <span className="text-xs">▼</span>
  </button>
  <div className="absolute right-0 top-full w-40 bg-white rounded-md shadow-lg py-1 hidden group-hover:block z-10">
    <button
      className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-blue-100"
      onClick={() => handleAddNew('student')}
    >
      Add Student
    </button>
    <button
      className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-green-100"
      onClick={() => handleAddNew('staff')}
    >
      Add Staff
    </button>
  </div>
</div>
      </div>

      {showQRPage ? (
        <QRCodeGenerationPage 
          selectedArchitectures={selectedArchitectures} 
          onBack={() => {
            setShowQRPage(false);
            setExistingTokens(null);
            fetchArchitectures();
          }}
          existingTokens={existingTokens}
        />
      ) : (
        <>
          {view === 'students' && (
            <div className="bg-white shadow-md rounded-lg p-3 sm:p-4 md:p-6 mt-4 w-full">
              <h2 className="text-base sm:text-lg md:text-xl font-semibold mb-3 sm:mb-4">Student Records</h2>
              
              {/* Search Bar */}
              <div className="mb-3 sm:mb-4">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search by ID, Name, Type, Department, Class, Division..."
                    className="w-full p-2 sm:p-3 border border-gray-300 rounded-lg pl-8 sm:pl-10 text-sm sm:text-base"
                    value={studentSearchTerm}
                    onChange={(e) => setStudentSearchTerm(e.target.value)}
                  />
                  <div className="absolute left-2 sm:left-3 top-2 sm:top-3 text-gray-400">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 sm:h-5 sm:w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                </div>
                {studentSearchTerm && (
                  <div className="text-xs sm:text-sm text-gray-600 mt-1 sm:mt-2">
                    Found {filteredStudentArchitectures.length} of {studentArchitectures.length} records
                  </div>
                )}
              </div>
              
              {/* Select All Button */}
              <div className="mb-3 sm:mb-4 flex flex-wrap items-center gap-2">
                <button
                  className="bg-gray-500 hover:bg-gray-700 text-white font-bold py-1 sm:py-2 px-2 sm:px-4 rounded text-xs sm:text-sm"
                  onClick={() => handleSelectAll(studentCurrentRecords)}
                >
                  {selectedRows.length === studentCurrentRecords.length && studentCurrentRecords.length > 0 ? 'Deselect All on Page' : 'Select All on Page'}
                </button>
                {selectedRows.length > 0 && (
                  <span className="text-xs sm:text-sm text-gray-600">
                    {selectedRows.length} item(s) selected total
                  </span>
                )}
                
                {/* QR Code Generation Button */}
                {selectedRows.length > 0 && (
                  <button 
                    className="ml-auto bg-purple-500 hover:bg-purple-700 text-white font-bold py-1 sm:py-2 px-2 sm:px-3 rounded text-xs sm:text-sm flex items-center gap-1"
                    onClick={handleGenerateQR}
                    title="Generate QR Codes for selected items"
                  >
                    <span>📋</span> 
                    <span className="hidden xs:inline">QR</span> 
                    <span className="hidden sm:inline">({selectedRows.length})</span>
                  </button>
                )}
              </div>
              
              {/* Desktop Table View - Hidden on mobile */}
              <div className="hidden md:block overflow-x-auto">
                <table className="min-w-full table-auto">
                  <thead>
                    <tr className="bg-gray-200 text-gray-600 uppercase text-xs leading-normal">
                      <th className="py-3 px-2 text-left">Sr. No.</th>
                      <th className="py-3 px-2 text-left">
                        <div className="flex items-center">
                          <input
                            type="checkbox"
                            className="mr-2"
                            checked={studentCurrentRecords.length > 0 && studentCurrentRecords.every(arch => selectedRows.includes(arch.id))}
                            onChange={() => {
                              const pageIds = studentCurrentRecords.map(arch => arch.id);
                              const allSelected = pageIds.every(id => selectedRows.includes(id));
                              
                              if (allSelected) {
                                setSelectedRows(selectedRows.filter(id => !pageIds.includes(id)));
                              } else {
                                const newSelected = [...new Set([...selectedRows, ...pageIds])];
                                setSelectedRows(newSelected);
                              }
                            }}
                          />
                          Select
                        </div>
                      </th>
                      <th className="py-3 px-2 text-left">Arch ID</th>
                      <th className="py-3 px-2 text-left">Name</th>
                      <th className="py-3 px-2 text-left">Type</th>
                      <th className="py-3 px-2 text-left">Department</th>
                      <th className="py-3 px-2 text-left">Class</th>
                      <th className="py-3 px-2 text-left">Division</th>
                      <th className="py-3 px-2 text-left">Students</th>
                      <th className="py-3 px-2 text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-600 text-sm font-light">
                    {studentCurrentRecords.length > 0 ? (
                      studentCurrentRecords.map((arch, index) => {
                        const actualIndex = studentIndexOfFirstRecord + index + 1;
                        return (
                          <tr key={arch.id} className="border-b border-gray-200 hover:bg-gray-100">
                            <td className="py-3 px-2 text-left">{actualIndex}</td>
                            <td className="py-3 px-2 text-left">
                              <input
                                type="checkbox"
                                checked={selectedRows.includes(arch.id)}
                                onChange={() => handleRowSelect(arch.id)}
                              />
                            </td>
                            <td className="py-3 px-2 text-left font-mono">{arch.id}</td>
                            <td className="py-3 px-2 text-left" title={arch.name}>{arch.name}</td>
                            <td className="py-3 px-2 text-left">{arch.institution_type || '-'}</td>
                            <td className="py-3 px-2 text-left">{arch.department_name || '-'}</td>
                            <td className="py-3 px-2 text-left">{arch.class_name || '-'}</td>
                            <td className="py-3 px-2 text-left">{arch.division || '-'}</td>
                            <td className="py-3 px-2 text-left">
                              {arch.tokenData && arch.tokenData.all.length > 0 ? (
                                <span className={`font-semibold ${
                                  arch.tokenData.all.length < arch.student_count ? 'text-orange-600' : 'text-green-600'
                                }`}>
                                  {arch.tokenData.all.length}
                                </span>
                              ) : (
                                <span>{arch.student_count}</span>
                              )}
                            </td>
                            {renderActionButtons(arch)}
                          </tr>
                        );
                      })
                    ) : (
                      <tr>
                        <td colSpan="10" className="text-center py-8 text-gray-500">
                          {studentSearchTerm ? 'No matching records found' : 'No student records available'}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              
              {/* Mobile Card View - Visible only on mobile/tablet */}
              <div className="md:hidden">
                {studentCurrentRecords.length > 0 ? (
                  studentCurrentRecords.map((arch, index) => {
                    const actualIndex = studentIndexOfFirstRecord + index + 1;
                    return (
                      <StudentMobileCard 
                        key={arch.id} 
                        arch={arch} 
                        index={index} 
                        actualIndex={actualIndex} 
                      />
                    );
                  })
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    {studentSearchTerm ? 'No matching records found' : 'No student records available'}
                  </div>
                )}
              </div>
              
              {/* Pagination Controls */}
              <StudentPagination />
            </div>
          )}

          {view === 'staff' && (
            <div className="bg-white shadow-md rounded-lg p-3 sm:p-4 md:p-6 mt-4 w-full">
              <h2 className="text-base sm:text-lg md:text-xl font-semibold mb-3 sm:mb-4">Staff Records</h2>
              
              {/* Search Bar */}
              <div className="mb-3 sm:mb-4">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search by ID, Name, Type, Department..."
                    className="w-full p-2 sm:p-3 border border-gray-300 rounded-lg pl-8 sm:pl-10 text-sm sm:text-base"
                    value={staffSearchTerm}
                    onChange={(e) => setStaffSearchTerm(e.target.value)}
                  />
                  <div className="absolute left-2 sm:left-3 top-2 sm:top-3 text-gray-400">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 sm:h-5 sm:w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                </div>
                {staffSearchTerm && (
                  <div className="text-xs sm:text-sm text-gray-600 mt-1 sm:mt-2">
                    Found {filteredStaffArchitectures.length} of {staffArchitectures.length} records
                  </div>
                )}
              </div>
              
              {/* Select All Button */}
              <div className="mb-3 sm:mb-4 flex flex-wrap items-center gap-2">
                <button
                  className="bg-gray-500 hover:bg-gray-700 text-white font-bold py-1 sm:py-2 px-2 sm:px-4 rounded text-xs sm:text-sm"
                  onClick={() => handleSelectAll(staffCurrentRecords)}
                >
                  {selectedRows.length === staffCurrentRecords.length && staffCurrentRecords.length > 0 ? 'Deselect All on Page' : 'Select All on Page'}
                </button>
                {selectedRows.length > 0 && (
                  <span className="text-xs sm:text-sm text-gray-600">
                    {selectedRows.length} item(s) selected total
                  </span>
                )}
                
                {/* QR Code Generation Button */}
                {selectedRows.length > 0 && (
                  <button 
                    className="ml-auto bg-purple-500 hover:bg-purple-700 text-white font-bold py-1 sm:py-2 px-2 sm:px-3 rounded text-xs sm:text-sm flex items-center gap-1"
                    onClick={handleGenerateQR}
                    title="Generate QR Codes for selected items"
                  >
                    <span>📋</span> 
                    <span className="hidden xs:inline">QR</span> 
                    <span className="hidden sm:inline">({selectedRows.length})</span>
                  </button>
                )}
              </div>
              
              {/* Desktop Table View - Hidden on mobile */}
              <div className="hidden md:block overflow-x-auto">
                <table className="min-w-full table-auto">
                  <thead>
                    <tr className="bg-gray-200 text-gray-600 uppercase text-xs leading-normal">
                      <th className="py-3 px-2 text-left">Sr. No.</th>
                      <th className="py-3 px-2 text-left">
                        <div className="flex items-center">
                          <input
                            type="checkbox"
                            className="mr-2"
                            checked={staffCurrentRecords.length > 0 && staffCurrentRecords.every(arch => selectedRows.includes(arch.id))}
                            onChange={() => {
                              const pageIds = staffCurrentRecords.map(arch => arch.id);
                              const allSelected = pageIds.every(id => selectedRows.includes(id));
                              
                              if (allSelected) {
                                setSelectedRows(selectedRows.filter(id => !pageIds.includes(id)));
                              } else {
                                const newSelected = [...new Set([...selectedRows, ...pageIds])];
                                setSelectedRows(newSelected);
                              }
                            }}
                          />
                          Select
                        </div>
                      </th>
                      <th className="py-3 px-2 text-left">Arch ID</th>
                      <th className="py-3 px-2 text-left">Name</th>
                      <th className="py-3 px-2 text-left">Type</th>
                      <th className="py-3 px-2 text-left">Department</th>
                      <th className="py-3 px-2 text-left">Staff</th>
                      <th className="py-3 px-2 text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-600 text-sm font-light">
                    {staffCurrentRecords.length > 0 ? (
                      staffCurrentRecords.map((arch, index) => {
                        const actualIndex = staffIndexOfFirstRecord + index + 1;
                        return (
                          <tr key={arch.id} className="border-b border-gray-200 hover:bg-gray-100">
                            <td className="py-3 px-2 text-left">{actualIndex}</td>
                            <td className="py-3 px-2 text-left">
                              <input
                                type="checkbox"
                                checked={selectedRows.includes(arch.id)}
                                onChange={() => handleRowSelect(arch.id)}
                              />
                            </td>
                            <td className="py-3 px-2 text-left font-mono">{arch.id}</td>
                            <td className="py-3 px-2 text-left" title={arch.name}>{arch.name}</td>
                            <td className="py-3 px-2 text-left">{arch.institution_type || '-'}</td>
                            <td className="py-3 px-2 text-left">{arch.department_name || '-'}</td>
                            <td className="py-3 px-2 text-left">
                              {arch.tokenData && arch.tokenData.all.length > 0 ? (
                                <span className={`font-semibold ${
                                  arch.tokenData.all.length < arch.staff_count ? 'text-orange-600' : 'text-green-600'
                                }`}>
                                  {arch.tokenData.all.length}
                                </span>
                              ) : (
                                <span>{arch.staff_count}</span>
                              )}
                            </td>
                            {renderActionButtons(arch)}
                          </tr>
                        );
                      })
                    ) : (
                      <tr>
                        <td colSpan="8" className="text-center py-8 text-gray-500">
                          {staffSearchTerm ? 'No matching records found' : 'No staff records available'}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              
              {/* Mobile Card View - Visible only on mobile/tablet */}
              <div className="md:hidden">
                {staffCurrentRecords.length > 0 ? (
                  staffCurrentRecords.map((arch, index) => {
                    const actualIndex = staffIndexOfFirstRecord + index + 1;
                    return (
                      <StaffMobileCard 
                        key={arch.id} 
                        arch={arch} 
                        index={index} 
                        actualIndex={actualIndex} 
                      />
                    );
                  })
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    {staffSearchTerm ? 'No matching records found' : 'No staff records available'}
                  </div>
                )}
              </div>
              
              {/* Pagination Controls */}
              <StaffPagination />
            </div>
          )}

          {view === 'tree' && (
            <div className="bg-white shadow-md rounded p-3 sm:p-4">
              <h2 className="text-lg sm:text-xl font-semibold mb-3 sm:mb-4">Architecture Tree</h2>
              {treeView.length > 0 ? (
                renderTree(treeView)
              ) : (
                <p className="text-gray-500 text-sm sm:text-base">No architecture data available.</p>
              )}
            </div>
          )}

          {view === 'detail' && (
            <div className="bg-white shadow-md rounded p-3 sm:p-4">
              <h2 className="text-lg sm:text-xl font-semibold mb-3 sm:mb-4">
                {isEditing ? 'Edit Architecture' : (formData.student_count > 0 ? 'Add New Student' : formData.staff_count > 0 ? 'Add New Staff' : 'Create New Architecture')}
              </h2>
              
              {/* Form Type Indicator */}
              {!isEditing && (
                <div className="mb-3 sm:mb-4">
                  {formData.student_count > 0 && (
                    <div className="bg-blue-100 text-blue-800 p-2 sm:p-3 rounded text-sm sm:text-base">
                      <strong>Creating Student Entry</strong>
                    </div>
                  )}
                  {formData.staff_count > 0 && (
                    <div className="bg-green-100 text-green-800 p-2 sm:p-3 rounded text-sm sm:text-base">
                      <strong>Creating Staff Entry</strong>
                    </div>
                  )}
                </div>
              )}
              
              <form onSubmit={isEditing ? handleUpdate : handleCreate} className="space-y-3 sm:space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                  <div>
                    <label className="block text-gray-700 text-xs sm:text-sm font-bold mb-1 sm:mb-2" htmlFor="name">
                      Name *
                    </label>
                    <input
                      id="name"
                      type="text"
                      className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline text-sm sm:text-base"
                      value={formData.name}
                      onChange={(e) => setFormData({...formData, name: e.target.value})}
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="block text-gray-700 text-xs sm:text-sm font-bold mb-1 sm:mb-2" htmlFor="institution_type">
                      Institution Type
                    </label>
                    <select
                      id="institution_type"
                      className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline text-sm sm:text-base"
                      value={formData.institution_type}
                      onChange={(e) => setFormData({...formData, institution_type: e.target.value})}
                    >
                      <option value="">Select Type</option>
                      {INSTITUTION_TYPES.map(type => (
                        <option key={type.value} value={type.value}>
                          {type.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                  <div>
                    <label className="block text-gray-700 text-xs sm:text-sm font-bold mb-1 sm:mb-2" htmlFor="department_name">
                      Department Name
                    </label>
                    <input
                      id="department_name"
                      type="text"
                      className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline text-sm sm:text-base"
                      value={formData.department_name}
                      onChange={(e) => setFormData({...formData, department_name: e.target.value})}
                    />
                  </div>
                  
                  {/* Show class name only for students */}
                  {formData.student_count > 0 && (
                    <div>
                      <label className="block text-gray-700 text-xs sm:text-sm font-bold mb-1 sm:mb-2" htmlFor="class_name">
                        Class Name
                      </label>
                      <input
                        id="class_name"
                        type="text"
                        className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline text-sm sm:text-base"
                        value={formData.class_name}
                        onChange={(e) => setFormData({...formData, class_name: e.target.value})}
                      />
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                  {/* Show division only for students */}
                  {formData.student_count > 0 && (
                    <div>
                      <label className="block text-gray-700 text-xs sm:text-sm font-bold mb-1 sm:mb-2" htmlFor="division">
                        Division
                      </label>
                      <input
                        id="division"
                        type="text"
                        className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline text-sm sm:text-base"
                        value={formData.division}
                        onChange={(e) => setFormData({...formData, division: e.target.value})}
                      />
                    </div>
                  )}
                  
                  <div className={formData.staff_count === 0 && formData.student_count === 0 ? "grid grid-cols-2 gap-3 sm:gap-4" : ""}>
                    {/* Show student count only for students */}
                    {formData.student_count > 0 && (
                      <div>
                        <label className="block text-gray-700 text-xs sm:text-sm font-bold mb-1 sm:mb-2" htmlFor="student_count">
                          Student Count
                        </label>
                        <input
                          id="student_count"
                          type="number"
                          min="1"
                          className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline text-sm sm:text-base"
                          // value={formData.student_count}
                          onChange={(e) => setFormData({...formData, student_count: parseInt(e.target.value) || 1})}
                        />
                      </div>
                    )}
                    
                    {/* Show staff count only for staff */}
                    {formData.staff_count > 0 && (
                      <div>
                        <label className="block text-gray-700 text-xs sm:text-sm font-bold mb-1 sm:mb-2" htmlFor="staff_count">
                          Staff Count
                        </label>
                        <input
                          id="staff_count"
                          type="number"
                          min="1"
                          className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline text-sm sm:text-base"
                          // value={formData.staff_count}
                          onChange={(e) => setFormData({...formData, staff_count: parseInt(e.target.value) || 1})}
                        />
                      </div>
                    )}
                  </div>
                </div>
                
                <div>
                  <label className="block text-gray-700 text-xs sm:text-sm font-bold mb-1 sm:mb-2" htmlFor="parent">
                    Parent Institution
                  </label>
                  <select
                    id="parent"
                    className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline text-sm sm:text-base"
                    value={formData.parent || ''}
                    onChange={(e) => setFormData({...formData, parent: e.target.value || null})}
                  >
                    <option value="">None</option>
                    {architectures.map(arch => (
                      <option key={arch.id} value={arch.id}>
                        {arch.name} {arch.institution_type && `(${arch.institution_type})`}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center">
                  <input
                    id="is_active"
                    type="checkbox"
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
                  />
                  <label htmlFor="is_active" className="ml-2 block text-xs sm:text-sm text-gray-900">
                    Active
                  </label>
                </div>

                <div className="flex flex-col sm:flex-row gap-2 sm:gap-4">
                  <button
                    type="submit"
                    className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded text-sm sm:text-base"
                  >
                    {isEditing ? 'Update' : 'Create'}
                  </button>
                  <button
                    type="button"
                    className="bg-gray-500 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded text-sm sm:text-base"
                    onClick={() => setView(previousView)}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ArchitectureManager;
  