import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { partsAPI, documentsAPI, importExportAPI, API_BASE } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Checkbox } from '../components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import {
  Truck, Upload, Download, Search, Plus, ChevronDown, ChevronRight,
  FileText, Trash2, Copy, Save, Edit2, X, CheckCircle2, AlertTriangle,
  XCircle, LogOut, FileSpreadsheet, Loader2
} from 'lucide-react';

const SupplierDashboard = () => {
  const { user, logout } = useAuth();
  const [stats, setStats] = useState({ completed: 0, incomplete: 0, needs_review: 0, total: 0 });
  const [parts, setParts] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [expandedParts, setExpandedParts] = useState({});
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Modals
  const [showUploadExcel, setShowUploadExcel] = useState(false);
  const [showUploadDoc, setShowUploadDoc] = useState(false);
  const [showAddPart, setShowAddPart] = useState(false);
  const [showAddChild, setShowAddChild] = useState(false);
  const [showEditChild, setShowEditChild] = useState(false);
  const [showManageDocs, setShowManageDocs] = useState(false);

  // Form states
  const [selectedPartId, setSelectedPartId] = useState(null);
  const [selectedChild, setSelectedChild] = useState(null);
  const [newPart, setNewPart] = useState({ sku: '', name: '', description: '', country_of_origin: '', total_weight_kg: 0, total_value_usd: 0 });
  const [newChild, setNewChild] = useState({
    identifier: '', name: '', description: '', country_of_origin: '', weight_kg: 0, value_usd: 0,
    aluminum_content_percent: 0, steel_content_percent: 0, has_russian_content: false,
    russian_content_percent: 0, russian_content_description: '', manufacturing_method: ''
  });
  const [selectedDocParts, setSelectedDocParts] = useState([]);
  const [selectedDocChildren, setSelectedDocChildren] = useState([]);
  const [uploadFile, setUploadFile] = useState(null);
  const [importResults, setImportResults] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [statsRes, partsRes, docsRes] = await Promise.all([
        partsAPI.getStats(),
        partsAPI.list(),
        documentsAPI.list()
      ]);
      setStats(statsRes.data);
      setParts(partsRes.data);
      setDocuments(docsRes.data);
    } catch (err) {
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const toggleExpanded = (partId) => {
    setExpandedParts(prev => ({ ...prev, [partId]: !prev[partId] }));
  };

  const filteredParts = parts.filter(part => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      part.sku?.toLowerCase().includes(q) ||
      part.name?.toLowerCase().includes(q) ||
      part.child_parts?.some(cp =>
        cp.identifier?.toLowerCase().includes(q) ||
        cp.name?.toLowerCase().includes(q)
      )
    );
  });

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      fetchData();
      return;
    }
    try {
      const response = await partsAPI.search(searchQuery);
      setParts(response.data);
    } catch (err) {
      setError('Search failed');
    }
  };

  const handleAddPart = async () => {
    try {
      await partsAPI.create(newPart);
      setShowAddPart(false);
      setNewPart({ sku: '', name: '', description: '', country_of_origin: '', total_weight_kg: 0, total_value_usd: 0 });
      setSuccess('Part created successfully');
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create part');
    }
  };

  const handleDeletePart = async (partId) => {
    if (!window.confirm('Are you sure you want to delete this part?')) return;
    try {
      await partsAPI.delete(partId);
      setSuccess('Part deleted successfully');
      fetchData();
    } catch (err) {
      setError('Failed to delete part');
    }
  };

  const handleAddChild = async () => {
    try {
      await partsAPI.addChild(selectedPartId, newChild);
      setShowAddChild(false);
      setNewChild({
        identifier: '', name: '', description: '', country_of_origin: '', weight_kg: 0, value_usd: 0,
        aluminum_content_percent: 0, steel_content_percent: 0, has_russian_content: false,
        russian_content_percent: 0, russian_content_description: '', manufacturing_method: ''
      });
      setSuccess('Component added successfully');
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add component');
    }
  };

  const handleUpdateChild = async () => {
    try {
      await partsAPI.updateChild(selectedPartId, selectedChild.id, selectedChild);
      setShowEditChild(false);
      setSuccess('Component updated successfully');
      fetchData();
    } catch (err) {
      setError('Failed to update component');
    }
  };

  const handleDeleteChild = async (partId, childId) => {
    if (!window.confirm('Are you sure you want to delete this component?')) return;
    try {
      await partsAPI.deleteChild(partId, childId);
      setSuccess('Component deleted successfully');
      fetchData();
    } catch (err) {
      setError('Failed to delete component');
    }
  };

  const handleDuplicateChild = async (partId, childId) => {
    try {
      await partsAPI.duplicateChild(partId, childId);
      setSuccess('Component duplicated successfully');
      fetchData();
    } catch (err) {
      setError('Failed to duplicate component');
    }
  };

  const handleExcelImport = async () => {
    if (!uploadFile) return;
    try {
      const response = await importExportAPI.importExcel(uploadFile);
      setImportResults(response.data);
      setSuccess('Import completed');
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Import failed');
    }
  };

  const handleDocUpload = async () => {
    if (!uploadFile) return;
    try {
      const response = await documentsAPI.upload(uploadFile, selectedDocParts, selectedDocChildren);
      if (response.data.duplicate_warning) {
        setSuccess('Document uploaded (replaced existing file with same name)');
      } else {
        setSuccess('Document uploaded successfully');
      }
      setShowUploadDoc(false);
      setUploadFile(null);
      setSelectedDocParts([]);
      setSelectedDocChildren([]);
      fetchData();
    } catch (err) {
      setError('Failed to upload document');
    }
  };

  const handleDeleteDocument = async (docId) => {
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    try {
      await documentsAPI.delete(docId);
      setSuccess('Document deleted');
      fetchData();
    } catch (err) {
      setError('Failed to delete document');
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-100 text-green-700 hover:bg-green-100"><CheckCircle2 className="w-3 h-3 mr-1" />Completed</Badge>;
      case 'needs_review':
        return <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-100"><AlertTriangle className="w-3 h-3 mr-1" />Needs Review</Badge>;
      default:
        return <Badge className="bg-red-100 text-red-700 hover:bg-red-100"><XCircle className="w-3 h-3 mr-1" />Incomplete</Badge>;
    }
  };

  const getDocumentsForChild = (childId) => {
    return documents.filter(doc => doc.child_part_ids?.includes(childId));
  };

  const getToken = () => localStorage.getItem('token');

  useEffect(() => {
    if (success || error) {
      const timer = setTimeout(() => {
        setSuccess('');
        setError('');
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [success, error]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-green-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-green-600 to-green-700 flex items-center justify-center">
                <Truck className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">RV Parts Portal</h1>
                <p className="text-xs text-gray-500">{user?.company_name || 'Supplier Dashboard'}</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600">{user?.name}</span>
              <Button variant="ghost" size="sm" onClick={logout} data-testid="logout-btn">
                <LogOut className="w-4 h-4 mr-2" />Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Alerts */}
        {error && (
          <Alert variant="destructive" className="mb-4" data-testid="error-alert">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {success && (
          <Alert className="mb-4 bg-green-50 border-green-200" data-testid="success-alert">
            <AlertDescription className="text-green-700">{success}</AlertDescription>
          </Alert>
        )}

        {/* Stats Tiles */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Card className="card-hover border-l-4 border-l-green-500" data-testid="stats-completed">
            <CardContent className="p-4">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-sm text-gray-500">Completed</p>
                  <p className="text-3xl font-bold text-green-600">{stats.completed}</p>
                </div>
                <CheckCircle2 className="w-10 h-10 text-green-200" />
              </div>
            </CardContent>
          </Card>

          <Card className="card-hover border-l-4 border-l-red-500" data-testid="stats-incomplete">
            <CardContent className="p-4">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-sm text-gray-500">Incomplete</p>
                  <p className="text-3xl font-bold text-red-600">{stats.incomplete}</p>
                </div>
                <XCircle className="w-10 h-10 text-red-200" />
              </div>
            </CardContent>
          </Card>

          <Card className="card-hover border-l-4 border-l-amber-500" data-testid="stats-review">
            <CardContent className="p-4">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-sm text-gray-500">Needs Review</p>
                  <p className="text-3xl font-bold text-amber-600">{stats.needs_review}</p>
                </div>
                <AlertTriangle className="w-10 h-10 text-amber-200" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-3 mb-6">
          <Button onClick={() => setShowUploadExcel(true)} variant="outline" className="gap-2" data-testid="upload-excel-btn">
            <FileSpreadsheet className="w-4 h-4" />Upload Excel
          </Button>
          <Button onClick={() => setShowUploadDoc(true)} variant="outline" className="gap-2" data-testid="upload-doc-btn">
            <Upload className="w-4 h-4" />Upload Document
          </Button>
          <a href={`${importExportAPI.downloadTemplate()}?token=${getToken()}`} target="_blank" rel="noreferrer">
            <Button variant="outline" className="gap-2" data-testid="download-template-btn">
              <Download className="w-4 h-4" />Download Template
            </Button>
          </a>
          <a href={`${importExportAPI.exportParts()}?token=${getToken()}`} target="_blank" rel="noreferrer">
            <Button variant="outline" className="gap-2" data-testid="export-parts-btn">
              <Download className="w-4 h-4" />Export Parts
            </Button>
          </a>
          <Button onClick={() => setShowManageDocs(true)} variant="outline" className="gap-2" data-testid="manage-docs-btn">
            <FileText className="w-4 h-4" />Manage Documents
          </Button>
        </div>

        {/* Search & Add Part */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <Input
              placeholder="Search by SKU or component name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="pl-10"
              data-testid="search-input"
            />
          </div>
          <Button onClick={() => setShowAddPart(true)} className="gap-2 bg-green-600 hover:bg-green-700" data-testid="add-part-btn">
            <Plus className="w-4 h-4" />Add Part
          </Button>
        </div>

        {/* Parts Table */}
        <Card>
          <CardHeader className="border-b">
            <CardTitle className="text-lg">Parts Management</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">SKU</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Country</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Weight (kg)</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Value (USD)</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredParts.map((part) => (
                    <React.Fragment key={part.id}>
                      {/* Parent Row */}
                      <tr className="bg-white hover:bg-gray-50 cursor-pointer" data-testid={`part-row-${part.sku}`}>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => toggleExpanded(part.id)}
                            className="flex items-center gap-2 font-medium text-gray-900"
                          >
                            {expandedParts[part.id] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                            {part.sku}
                          </button>
                        </td>
                        <td className="px-4 py-3 text-gray-700">{part.name}</td>
                        <td className="px-4 py-3 text-gray-700">{part.country_of_origin || '-'}</td>
                        <td className="px-4 py-3 text-gray-700">{part.total_weight_kg?.toFixed(2)}</td>
                        <td className="px-4 py-3 text-gray-700">${part.total_value_usd?.toFixed(2)}</td>
                        <td className="px-4 py-3">{getStatusBadge(part.status)}</td>
                        <td className="px-4 py-3">
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                setSelectedPartId(part.id);
                                setShowAddChild(true);
                              }}
                              title="Add Component"
                              data-testid={`add-child-${part.sku}`}
                            >
                              <Plus className="w-4 h-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-red-600 hover:text-red-700"
                              onClick={() => handleDeletePart(part.id)}
                              title="Delete Part"
                              data-testid={`delete-part-${part.sku}`}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </td>
                      </tr>

                      {/* Child Rows */}
                      {expandedParts[part.id] && part.child_parts?.map((child) => (
                        <tr key={child.id} className="bg-gray-50 hover:bg-gray-100" data-testid={`child-row-${child.identifier}`}>
                          <td className="px-4 py-3 pl-12">
                            <span className="text-gray-600 text-sm">└─ {child.identifier}</span>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600">{child.name}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{child.country_of_origin}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{child.weight_kg?.toFixed(2)}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">${child.value_usd?.toFixed(2)}</td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              {child.is_complete ? (
                                <Badge variant="outline" className="text-green-600 border-green-300">Complete</Badge>
                              ) : (
                                <Badge variant="outline" className="text-red-600 border-red-300">Incomplete</Badge>
                              )}
                              {getDocumentsForChild(child.id).length > 0 && (
                                <button
                                  onClick={() => {
                                    const docs = getDocumentsForChild(child.id);
                                    if (docs.length > 0) {
                                      window.open(`${API_BASE}/documents/${docs[0].id}/download`, '_blank');
                                    }
                                  }}
                                  className="text-blue-600 hover:text-blue-700"
                                  title="View Document"
                                >
                                  <FileText className="w-4 h-4" />
                                </button>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex gap-1">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => {
                                  setSelectedPartId(part.id);
                                  setSelectedChild({ ...child });
                                  setShowEditChild(true);
                                }}
                                title="Edit"
                                data-testid={`edit-child-${child.identifier}`}
                              >
                                <Edit2 className="w-4 h-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleDuplicateChild(part.id, child.id)}
                                title="Duplicate"
                                data-testid={`duplicate-child-${child.identifier}`}
                              >
                                <Copy className="w-4 h-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-red-600 hover:text-red-700"
                                onClick={() => handleDeleteChild(part.id, child.id)}
                                title="Delete"
                                data-testid={`delete-child-${child.identifier}`}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}

                      {expandedParts[part.id] && (!part.child_parts || part.child_parts.length === 0) && (
                        <tr className="bg-gray-50">
                          <td colSpan="7" className="px-4 py-3 pl-12 text-sm text-gray-500 italic">
                            No components added yet
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                  {filteredParts.length === 0 && (
                    <tr>
                      <td colSpan="7" className="px-4 py-8 text-center text-gray-500">
                        No parts found. Click "Add Part" to create your first part.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </main>

      {/* Add Part Modal */}
      <Dialog open={showAddPart} onOpenChange={setShowAddPart}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add New Part</DialogTitle>
            <DialogDescription>Create a new parent SKU</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>SKU *</Label>
              <Input value={newPart.sku} onChange={(e) => setNewPart({ ...newPart, sku: e.target.value })} placeholder="e.g., RV-PART-001" data-testid="new-part-sku" />
            </div>
            <div>
              <Label>Name *</Label>
              <Input value={newPart.name} onChange={(e) => setNewPart({ ...newPart, name: e.target.value })} placeholder="Part name" data-testid="new-part-name" />
            </div>
            <div>
              <Label>Description</Label>
              <Input value={newPart.description} onChange={(e) => setNewPart({ ...newPart, description: e.target.value })} placeholder="Description" />
            </div>
            <div>
              <Label>Country of Origin</Label>
              <Input value={newPart.country_of_origin} onChange={(e) => setNewPart({ ...newPart, country_of_origin: e.target.value })} placeholder="e.g., USA" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Total Weight (kg)</Label>
                <Input type="number" step="0.01" value={newPart.total_weight_kg} onChange={(e) => setNewPart({ ...newPart, total_weight_kg: parseFloat(e.target.value) || 0 })} />
              </div>
              <div>
                <Label>Total Value (USD)</Label>
                <Input type="number" step="0.01" value={newPart.total_value_usd} onChange={(e) => setNewPart({ ...newPart, total_value_usd: parseFloat(e.target.value) || 0 })} />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddPart(false)}>Cancel</Button>
            <Button onClick={handleAddPart} className="bg-green-600 hover:bg-green-700" data-testid="save-new-part">Create Part</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Child Modal */}
      <Dialog open={showAddChild} onOpenChange={setShowAddChild}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Add Component</DialogTitle>
            <DialogDescription>Add a new component to this part</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Identifier *</Label>
                <Input value={newChild.identifier} onChange={(e) => setNewChild({ ...newChild, identifier: e.target.value })} placeholder="e.g., COMP-001" data-testid="new-child-id" />
              </div>
              <div>
                <Label>Name *</Label>
                <Input value={newChild.name} onChange={(e) => setNewChild({ ...newChild, name: e.target.value })} placeholder="Component name" data-testid="new-child-name" />
              </div>
            </div>
            <div>
              <Label>Description</Label>
              <Input value={newChild.description} onChange={(e) => setNewChild({ ...newChild, description: e.target.value })} placeholder="Description" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Country of Origin *</Label>
                <Input value={newChild.country_of_origin} onChange={(e) => setNewChild({ ...newChild, country_of_origin: e.target.value })} placeholder="e.g., USA" />
              </div>
              <div>
                <Label>Manufacturing Method</Label>
                <Input value={newChild.manufacturing_method} onChange={(e) => setNewChild({ ...newChild, manufacturing_method: e.target.value })} placeholder="e.g., Welded" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Weight (kg) *</Label>
                <Input type="number" step="0.01" value={newChild.weight_kg} onChange={(e) => setNewChild({ ...newChild, weight_kg: parseFloat(e.target.value) || 0 })} />
              </div>
              <div>
                <Label>Value (USD) *</Label>
                <Input type="number" step="0.01" value={newChild.value_usd} onChange={(e) => setNewChild({ ...newChild, value_usd: parseFloat(e.target.value) || 0 })} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Aluminum Content (%)</Label>
                <Input type="number" step="0.1" value={newChild.aluminum_content_percent} onChange={(e) => setNewChild({ ...newChild, aluminum_content_percent: parseFloat(e.target.value) || 0 })} />
              </div>
              <div>
                <Label>Steel Content (%)</Label>
                <Input type="number" step="0.1" value={newChild.steel_content_percent} onChange={(e) => setNewChild({ ...newChild, steel_content_percent: parseFloat(e.target.value) || 0 })} />
              </div>
            </div>
            <div className="border-t pt-4">
              <div className="flex items-center gap-2 mb-2">
                <Checkbox
                  id="russian-content"
                  checked={newChild.has_russian_content}
                  onCheckedChange={(checked) => setNewChild({ ...newChild, has_russian_content: checked })}
                />
                <Label htmlFor="russian-content">Has Russian Content</Label>
              </div>
              {newChild.has_russian_content && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Russian Content (%)</Label>
                    <Input type="number" step="0.1" value={newChild.russian_content_percent} onChange={(e) => setNewChild({ ...newChild, russian_content_percent: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label>Description</Label>
                    <Input value={newChild.russian_content_description} onChange={(e) => setNewChild({ ...newChild, russian_content_description: e.target.value })} placeholder="Details" />
                  </div>
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddChild(false)}>Cancel</Button>
            <Button onClick={handleAddChild} className="bg-green-600 hover:bg-green-700" data-testid="save-new-child">Add Component</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Child Modal */}
      <Dialog open={showEditChild} onOpenChange={setShowEditChild}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Component</DialogTitle>
            <DialogDescription>Update component details</DialogDescription>
          </DialogHeader>
          {selectedChild && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Identifier</Label>
                  <Input value={selectedChild.identifier} onChange={(e) => setSelectedChild({ ...selectedChild, identifier: e.target.value })} />
                </div>
                <div>
                  <Label>Name</Label>
                  <Input value={selectedChild.name} onChange={(e) => setSelectedChild({ ...selectedChild, name: e.target.value })} />
                </div>
              </div>
              <div>
                <Label>Description</Label>
                <Input value={selectedChild.description || ''} onChange={(e) => setSelectedChild({ ...selectedChild, description: e.target.value })} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Country of Origin</Label>
                  <Input value={selectedChild.country_of_origin} onChange={(e) => setSelectedChild({ ...selectedChild, country_of_origin: e.target.value })} />
                </div>
                <div>
                  <Label>Manufacturing Method</Label>
                  <Input value={selectedChild.manufacturing_method || ''} onChange={(e) => setSelectedChild({ ...selectedChild, manufacturing_method: e.target.value })} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Weight (kg)</Label>
                  <Input type="number" step="0.01" value={selectedChild.weight_kg} onChange={(e) => setSelectedChild({ ...selectedChild, weight_kg: parseFloat(e.target.value) || 0 })} />
                </div>
                <div>
                  <Label>Value (USD)</Label>
                  <Input type="number" step="0.01" value={selectedChild.value_usd} onChange={(e) => setSelectedChild({ ...selectedChild, value_usd: parseFloat(e.target.value) || 0 })} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Aluminum (%)</Label>
                  <Input type="number" step="0.1" value={selectedChild.aluminum_content_percent} onChange={(e) => setSelectedChild({ ...selectedChild, aluminum_content_percent: parseFloat(e.target.value) || 0 })} />
                </div>
                <div>
                  <Label>Steel (%)</Label>
                  <Input type="number" step="0.1" value={selectedChild.steel_content_percent} onChange={(e) => setSelectedChild({ ...selectedChild, steel_content_percent: parseFloat(e.target.value) || 0 })} />
                </div>
              </div>
              <div className="border-t pt-4">
                <div className="flex items-center gap-2 mb-2">
                  <Checkbox
                    id="edit-russian-content"
                    checked={selectedChild.has_russian_content}
                    onCheckedChange={(checked) => setSelectedChild({ ...selectedChild, has_russian_content: checked })}
                  />
                  <Label htmlFor="edit-russian-content">Has Russian Content</Label>
                </div>
                {selectedChild.has_russian_content && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Russian Content (%)</Label>
                      <Input type="number" step="0.1" value={selectedChild.russian_content_percent} onChange={(e) => setSelectedChild({ ...selectedChild, russian_content_percent: parseFloat(e.target.value) || 0 })} />
                    </div>
                    <div>
                      <Label>Description</Label>
                      <Input value={selectedChild.russian_content_description || ''} onChange={(e) => setSelectedChild({ ...selectedChild, russian_content_description: e.target.value })} />
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditChild(false)}>Cancel</Button>
            <Button onClick={handleUpdateChild} className="bg-green-600 hover:bg-green-700" data-testid="save-edit-child"><Save className="w-4 h-4 mr-2" />Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Upload Excel Modal */}
      <Dialog open={showUploadExcel} onOpenChange={(open) => { setShowUploadExcel(open); if (!open) { setUploadFile(null); setImportResults(null); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Import Excel File</DialogTitle>
            <DialogDescription>Upload an Excel file to batch update parts data</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
              <input
                type="file"
                accept=".xlsx,.xls"
                onChange={(e) => setUploadFile(e.target.files[0])}
                className="hidden"
                id="excel-upload"
              />
              <label htmlFor="excel-upload" className="cursor-pointer">
                <FileSpreadsheet className="w-12 h-12 mx-auto text-gray-400 mb-2" />
                <p className="text-sm text-gray-600">
                  {uploadFile ? uploadFile.name : 'Click to select or drag & drop your Excel file'}
                </p>
              </label>
            </div>
            {importResults && (
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="font-medium mb-2">Import Results:</p>
                <ul className="text-sm space-y-1">
                  <li className="text-green-600">✓ {importResults.created_parents} parents created</li>
                  <li className="text-blue-600">↻ {importResults.updated_parents} parents updated</li>
                  <li className="text-green-600">✓ {importResults.created_children} components created</li>
                  <li className="text-blue-600">↻ {importResults.updated_children} components updated</li>
                  {importResults.errors?.length > 0 && (
                    <li className="text-red-600">✗ {importResults.errors.length} errors</li>
                  )}
                </ul>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowUploadExcel(false)}>Close</Button>
            <Button onClick={handleExcelImport} disabled={!uploadFile} className="bg-green-600 hover:bg-green-700" data-testid="import-excel-submit"><Upload className="w-4 h-4 mr-2" />Import</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Upload Document Modal */}
      <Dialog open={showUploadDoc} onOpenChange={(open) => { setShowUploadDoc(open); if (!open) { setUploadFile(null); setSelectedDocParts([]); setSelectedDocChildren([]); } }}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Upload Document</DialogTitle>
            <DialogDescription>Upload a document and assign it to parts/components</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
              <input
                type="file"
                accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg"
                onChange={(e) => setUploadFile(e.target.files[0])}
                className="hidden"
                id="doc-upload"
              />
              <label htmlFor="doc-upload" className="cursor-pointer">
                <FileText className="w-12 h-12 mx-auto text-gray-400 mb-2" />
                <p className="text-sm text-gray-600">
                  {uploadFile ? uploadFile.name : 'Click to select your document'}
                </p>
              </label>
            </div>
            
            <div>
              <Label className="mb-2 block">Assign to Parent SKUs:</Label>
              <div className="max-h-32 overflow-y-auto border rounded-lg p-2 space-y-1">
                {parts.map(part => (
                  <div key={part.id} className="flex items-center gap-2">
                    <Checkbox
                      id={`doc-part-${part.id}`}
                      checked={selectedDocParts.includes(part.id)}
                      onCheckedChange={(checked) => {
                        if (checked) {
                          setSelectedDocParts([...selectedDocParts, part.id]);
                        } else {
                          setSelectedDocParts(selectedDocParts.filter(id => id !== part.id));
                        }
                      }}
                    />
                    <Label htmlFor={`doc-part-${part.id}`} className="text-sm">{part.sku} - {part.name}</Label>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <Label className="mb-2 block">Assign to Components:</Label>
              <div className="max-h-40 overflow-y-auto border rounded-lg p-2 space-y-2">
                {parts.map(part => (
                  <div key={part.id}>
                    <p className="text-xs font-medium text-gray-500 mb-1">{part.sku}</p>
                    {part.child_parts?.map(child => (
                      <div key={child.id} className="flex items-center gap-2 ml-4">
                        <Checkbox
                          id={`doc-child-${child.id}`}
                          checked={selectedDocChildren.includes(child.id)}
                          onCheckedChange={(checked) => {
                            if (checked) {
                              setSelectedDocChildren([...selectedDocChildren, child.id]);
                            } else {
                              setSelectedDocChildren(selectedDocChildren.filter(id => id !== child.id));
                            }
                          }}
                        />
                        <Label htmlFor={`doc-child-${child.id}`} className="text-sm">{child.identifier}</Label>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowUploadDoc(false)}>Cancel</Button>
            <Button onClick={handleDocUpload} disabled={!uploadFile} className="bg-green-600 hover:bg-green-700" data-testid="upload-doc-submit"><Upload className="w-4 h-4 mr-2" />Upload</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Manage Documents Modal */}
      <Dialog open={showManageDocs} onOpenChange={setShowManageDocs}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Manage Documents</DialogTitle>
            <DialogDescription>View, rename, or delete your uploaded documents</DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            {documents.length === 0 ? (
              <p className="text-center text-gray-500 py-8">No documents uploaded yet</p>
            ) : (
              documents.map(doc => (
                <div key={doc.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <FileText className="w-8 h-8 text-blue-500" />
                    <div>
                      <p className="font-medium text-sm">{doc.original_name}</p>
                      <p className="text-xs text-gray-500">
                        {(doc.file_size / 1024).toFixed(1)} KB • 
                        {doc.parent_part_ids?.length || 0} parts • 
                        {doc.child_part_ids?.length || 0} components
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <a href={`${API_BASE}/documents/${doc.id}/download`} target="_blank" rel="noreferrer">
                      <Button size="sm" variant="outline"><Download className="w-4 h-4" /></Button>
                    </a>
                    <Button size="sm" variant="outline" className="text-red-600" onClick={() => handleDeleteDocument(doc.id)}><Trash2 className="w-4 h-4" /></Button>
                  </div>
                </div>
              ))
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowManageDocs(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SupplierDashboard;
