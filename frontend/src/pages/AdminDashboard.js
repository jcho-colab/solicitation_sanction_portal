import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { partsAPI, suppliersAPI, auditAPI, importExportAPI, API_BASE } from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Switch } from '../components/ui/switch';
import {
  Users, Package, FileText, ClipboardList, Download,
  Plus, Trash2, Edit2, LogOut, Search, CheckCircle2, AlertTriangle,
  XCircle, Loader2, ChevronDown, ChevronRight
} from 'lucide-react';

// BRP Logo URL
const BRP_LOGO = 'https://customer-assets.emergentagent.com/job_de62b586-37dc-482e-9f01-b4c01458fc65/artifacts/h5zfso2l_BRP_inc_logo.svg.png';

const AdminDashboard = () => {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Data states
  const [suppliers, setSuppliers] = useState([]);
  const [allParts, setAllParts] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [stats, setStats] = useState({ completed: 0, incomplete: 0, needs_review: 0, total: 0 });
  const [expandedParts, setExpandedParts] = useState({});

  // Modal states
  const [showAddSupplier, setShowAddSupplier] = useState(false);
  const [showEditSupplier, setShowEditSupplier] = useState(false);
  const [selectedSupplier, setSelectedSupplier] = useState(null);

  // Form states
  const [newSupplier, setNewSupplier] = useState({ email: '', password: '', name: '', company_name: '' });

  // Filter states
  const [auditFilter, setAuditFilter] = useState({ supplier_id: '', entity_type: '' });
  const [searchQuery, setSearchQuery] = useState('');

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [suppliersRes, partsRes, statsRes] = await Promise.all([
        suppliersAPI.list(),
        partsAPI.list(),
        partsAPI.getStats()
      ]);
      setSuppliers(suppliersRes.data);
      setAllParts(partsRes.data);
      setStats(statsRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAuditLogs = useCallback(async () => {
    try {
      const response = await auditAPI.list({
        supplier_id: auditFilter.supplier_id || undefined,
        entity_type: auditFilter.entity_type || undefined,
        limit: 100
      });
      setAuditLogs(response.data);
    } catch (err) {
      console.error(err);
    }
  }, [auditFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (activeTab === 'audit') {
      fetchAuditLogs();
    }
  }, [activeTab, fetchAuditLogs]);

  const handleAddSupplier = async () => {
    try {
      await suppliersAPI.create(newSupplier);
      setShowAddSupplier(false);
      setNewSupplier({ email: '', password: '', name: '', company_name: '' });
      setSuccess('Supplier created successfully');
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create supplier');
    }
  };

  const handleUpdateSupplier = async () => {
    try {
      await suppliersAPI.update(selectedSupplier.id, {
        name: selectedSupplier.name,
        company_name: selectedSupplier.company_name,
        is_active: selectedSupplier.is_active
      });
      setShowEditSupplier(false);
      setSuccess('Supplier updated successfully');
      fetchData();
    } catch (err) {
      setError('Failed to update supplier');
    }
  };

  const handleDeleteSupplier = async (supplierId) => {
    if (!window.confirm('Are you sure you want to delete this supplier?')) return;
    try {
      await suppliersAPI.delete(supplierId);
      setSuccess('Supplier deleted successfully');
      fetchData();
    } catch (err) {
      setError('Failed to delete supplier');
    }
  };

  const toggleExpanded = (partId) => {
    setExpandedParts(prev => ({ ...prev, [partId]: !prev[partId] }));
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

  const getSupplierName = (supplierId) => {
    const supplier = suppliers.find(s => s.id === supplierId);
    return supplier?.company_name || supplier?.name || 'Unknown';
  };

  const filteredParts = allParts.filter(part => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      part.sku?.toLowerCase().includes(q) ||
      part.name?.toLowerCase().includes(q)
    );
  });

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
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-yellow-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header - BRP Branding */}
      <header className="brp-header sticky top-0 z-40 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-4">
              <img src={BRP_LOGO} alt="BRP" className="h-10 w-auto" />
              <div className="border-l border-gray-600 pl-4">
                <h1 className="text-lg font-semibold text-white">Parts Portal</h1>
                <p className="text-xs text-yellow-500">Admin Dashboard</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <Badge variant="outline" className="bg-yellow-600 text-white border-yellow-500">Admin</Badge>
              <span className="text-sm text-gray-300">{user?.name}</span>
              <Button variant="ghost" size="sm" onClick={logout} className="text-white hover:bg-gray-700" data-testid="admin-logout-btn">
                <LogOut className="w-4 h-4 mr-2" />Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Alerts */}
        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {success && (
          <Alert className="mb-4 bg-green-50 border-green-200">
            <AlertDescription className="text-green-700">{success}</AlertDescription>
          </Alert>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 lg:w-auto lg:inline-flex">
            <TabsTrigger value="overview" className="gap-2" data-testid="tab-overview">
              <Package className="w-4 h-4" />Overview
            </TabsTrigger>
            <TabsTrigger value="suppliers" className="gap-2" data-testid="tab-suppliers">
              <Users className="w-4 h-4" />Suppliers
            </TabsTrigger>
            <TabsTrigger value="parts" className="gap-2" data-testid="tab-parts">
              <FileText className="w-4 h-4" />All Parts
            </TabsTrigger>
            <TabsTrigger value="audit" className="gap-2" data-testid="tab-audit">
              <ClipboardList className="w-4 h-4" />Audit Logs
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card className="border-l-4 border-l-blue-500">
                <CardContent className="p-4">
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="text-sm text-gray-500">Total Suppliers</p>
                      <p className="text-3xl font-bold text-blue-600">{suppliers.length}</p>
                    </div>
                    <Users className="w-10 h-10 text-blue-200" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-l-4 border-l-green-500">
                <CardContent className="p-4">
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="text-sm text-gray-500">Completed Parts</p>
                      <p className="text-3xl font-bold text-green-600">{stats.completed}</p>
                    </div>
                    <CheckCircle2 className="w-10 h-10 text-green-200" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-l-4 border-l-red-500">
                <CardContent className="p-4">
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="text-sm text-gray-500">Incomplete Parts</p>
                      <p className="text-3xl font-bold text-red-600">{stats.incomplete}</p>
                    </div>
                    <XCircle className="w-10 h-10 text-red-200" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-l-4 border-l-amber-500">
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

            {/* Suppliers Overview */}
            <Card>
              <CardHeader>
                <CardTitle>Suppliers Overview</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Contact</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Parts</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {suppliers.map(supplier => {
                        const supplierParts = allParts.filter(p => p.supplier_id === supplier.id);
                        const completed = supplierParts.filter(p => p.status === 'completed').length;
                        return (
                          <tr key={supplier.id} className="hover:bg-gray-50">
                            <td className="px-4 py-3 font-medium">{supplier.company_name || '-'}</td>
                            <td className="px-4 py-3">
                              <div>
                                <p className="text-sm">{supplier.name}</p>
                                <p className="text-xs text-gray-500">{supplier.email}</p>
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <span className="text-green-600 font-medium">{completed}</span>
                              <span className="text-gray-400"> / {supplierParts.length}</span>
                            </td>
                            <td className="px-4 py-3">
                              {supplier.is_active !== false ? (
                                <Badge className="bg-green-100 text-green-700">Active</Badge>
                              ) : (
                                <Badge className="bg-gray-100 text-gray-700">Inactive</Badge>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Suppliers Tab */}
          <TabsContent value="suppliers" className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold">Manage Suppliers</h2>
              <Button onClick={() => setShowAddSupplier(true)} className="gap-2 bg-yellow-600 hover:bg-yellow-700" data-testid="add-supplier-btn">
                <Plus className="w-4 h-4" />Add Supplier
              </Button>
            </div>

            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {suppliers.map(supplier => (
                        <tr key={supplier.id} className="hover:bg-gray-50" data-testid={`supplier-row-${supplier.email}`}>
                          <td className="px-4 py-3 font-medium">{supplier.name}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{supplier.email}</td>
                          <td className="px-4 py-3">{supplier.company_name || '-'}</td>
                          <td className="px-4 py-3">
                            {supplier.is_active !== false ? (
                              <Badge className="bg-green-100 text-green-700">Active</Badge>
                            ) : (
                              <Badge className="bg-gray-100 text-gray-700">Inactive</Badge>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => {
                                  setSelectedSupplier({ ...supplier });
                                  setShowEditSupplier(true);
                                }}
                              >
                                <Edit2 className="w-4 h-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-red-600"
                                onClick={() => handleDeleteSupplier(supplier.id)}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                      {suppliers.length === 0 && (
                        <tr>
                          <td colSpan="5" className="px-4 py-8 text-center text-gray-500">
                            No suppliers yet. Click &quot;Add Supplier&quot; to create one.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* All Parts Tab */}
          <TabsContent value="parts" className="space-y-4">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
              <h2 className="text-lg font-semibold">All Parts</h2>
              <div className="flex gap-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    placeholder="Search parts..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10 w-64"
                  />
                </div>
                <a href={`${importExportAPI.exportParts()}`} target="_blank" rel="noreferrer">
                  <Button variant="outline" className="gap-2">
                    <Download className="w-4 h-4" />Export All
                  </Button>
                </a>
              </div>
            </div>

            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">SKU</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Supplier</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Country</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Weight</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Value</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Components</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {filteredParts.map(part => (
                        <React.Fragment key={part.id}>
                          <tr className="hover:bg-gray-50 cursor-pointer" onClick={() => toggleExpanded(part.id)}>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2 font-medium">
                                {expandedParts[part.id] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                                {part.sku}
                              </div>
                            </td>
                            <td className="px-4 py-3">{part.name}</td>
                            <td className="px-4 py-3 text-sm">{getSupplierName(part.supplier_id)}</td>
                            <td className="px-4 py-3 text-sm">{part.country_of_origin || '-'}</td>
                            <td className="px-4 py-3 text-sm">{part.total_weight_kg?.toFixed(2)} kg</td>
                            <td className="px-4 py-3 text-sm">${part.total_value_usd?.toFixed(2)}</td>
                            <td className="px-4 py-3">{getStatusBadge(part.status)}</td>
                            <td className="px-4 py-3 text-sm">{part.child_parts?.length || 0}</td>
                          </tr>
                          {expandedParts[part.id] && part.child_parts?.map(child => (
                            <tr key={child.id} className="bg-gray-50">
                              <td className="px-4 py-2 pl-12 text-sm text-gray-600">└─ {child.identifier}</td>
                              <td className="px-4 py-2 text-sm text-gray-600">{child.name}</td>
                              <td className="px-4 py-2 text-sm text-gray-500">-</td>
                              <td className="px-4 py-2 text-sm text-gray-600">{child.country_of_origin}</td>
                              <td className="px-4 py-2 text-sm text-gray-600">{child.weight_kg?.toFixed(2)} kg</td>
                              <td className="px-4 py-2 text-sm text-gray-600">${child.value_usd?.toFixed(2)}</td>
                              <td className="px-4 py-2">
                                {child.is_complete ? (
                                  <Badge variant="outline" className="text-xs text-green-600 border-green-300">Complete</Badge>
                                ) : (
                                  <Badge variant="outline" className="text-xs text-red-600 border-red-300">Incomplete</Badge>
                                )}
                              </td>
                              <td className="px-4 py-2">
                                <div className="text-xs space-x-2">
                                  {child.aluminum_content_percent > 0 && <span className="text-blue-600">Al: {child.aluminum_content_percent}%</span>}
                                  {child.steel_content_percent > 0 && <span className="text-gray-600">Steel: {child.steel_content_percent}%</span>}
                                  {child.has_russian_content && <span className="text-red-600">RU: {child.russian_content_percent}%</span>}
                                </div>
                              </td>
                            </tr>
                          ))}
                        </React.Fragment>
                      ))}
                      {filteredParts.length === 0 && (
                        <tr>
                          <td colSpan="8" className="px-4 py-8 text-center text-gray-500">
                            No parts found
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Audit Logs Tab */}
          <TabsContent value="audit" className="space-y-4">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
              <h2 className="text-lg font-semibold">Audit Logs</h2>
              <div className="flex flex-wrap gap-3">
                <Select value={auditFilter.supplier_id} onValueChange={(v) => setAuditFilter({ ...auditFilter, supplier_id: v })}>
                  <SelectTrigger className="w-48">
                    <SelectValue placeholder="Filter by supplier" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Suppliers</SelectItem>
                    {suppliers.map(s => (
                      <SelectItem key={s.id} value={s.id}>{s.company_name || s.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={auditFilter.entity_type} onValueChange={(v) => setAuditFilter({ ...auditFilter, entity_type: v })}>
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Filter by type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Types</SelectItem>
                    <SelectItem value="parent_part">Parent Parts</SelectItem>
                    <SelectItem value="child_part">Child Parts</SelectItem>
                    <SelectItem value="document">Documents</SelectItem>
                    <SelectItem value="supplier">Suppliers</SelectItem>
                    <SelectItem value="batch_import">Imports</SelectItem>
                  </SelectContent>
                </Select>
                <a href={auditAPI.exportUrl(auditFilter)} target="_blank" rel="noreferrer">
                  <Button variant="outline" className="gap-2">
                    <Download className="w-4 h-4" />Export Logs
                  </Button>
                </a>
              </div>
            </div>

            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Timestamp</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Entity Type</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Changes</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {auditLogs.map(log => (
                        <tr key={log.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm text-gray-600">
                            {new Date(log.timestamp).toLocaleString()}
                          </td>
                          <td className="px-4 py-3 text-sm">{log.user_email}</td>
                          <td className="px-4 py-3">
                            <Badge variant="outline" className={{
                              'create': 'text-green-600 border-green-300',
                              'update': 'text-blue-600 border-blue-300',
                              'delete': 'text-red-600 border-red-300',
                              'import': 'text-purple-600 border-purple-300'
                            }[log.action] || ''}>
                              {log.action}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-sm">{log.entity_type?.replace('_', ' ')}</td>
                          <td className="px-4 py-3 text-sm">
                            <div className="max-w-xs truncate">
                              {log.field_changes?.map((change, i) => (
                                <span key={i} className="text-xs">
                                  {change.field}: {change.old || '-'} → {change.new || '-'}
                                  {i < log.field_changes.length - 1 && ', '}
                                </span>
                              ))}
                            </div>
                          </td>
                        </tr>
                      ))}
                      {auditLogs.length === 0 && (
                        <tr>
                          <td colSpan="5" className="px-4 py-8 text-center text-gray-500">
                            No audit logs found
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Add Supplier Modal */}
      <Dialog open={showAddSupplier} onOpenChange={setShowAddSupplier}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add New Supplier</DialogTitle>
            <DialogDescription>Create a new supplier account</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Name *</Label>
              <Input
                value={newSupplier.name}
                onChange={(e) => setNewSupplier({ ...newSupplier, name: e.target.value })}
                placeholder="Contact name"
                data-testid="new-supplier-name"
              />
            </div>
            <div>
              <Label>Email *</Label>
              <Input
                type="email"
                value={newSupplier.email}
                onChange={(e) => setNewSupplier({ ...newSupplier, email: e.target.value })}
                placeholder="supplier@company.com"
                data-testid="new-supplier-email"
              />
            </div>
            <div>
              <Label>Password *</Label>
              <Input
                type="password"
                value={newSupplier.password}
                onChange={(e) => setNewSupplier({ ...newSupplier, password: e.target.value })}
                placeholder="Initial password"
                data-testid="new-supplier-password"
              />
            </div>
            <div>
              <Label>Company Name</Label>
              <Input
                value={newSupplier.company_name}
                onChange={(e) => setNewSupplier({ ...newSupplier, company_name: e.target.value })}
                placeholder="Company LLC"
                data-testid="new-supplier-company"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddSupplier(false)}>Cancel</Button>
            <Button onClick={handleAddSupplier} className="bg-yellow-600 hover:bg-yellow-700" data-testid="save-new-supplier">Create Supplier</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Supplier Modal */}
      <Dialog open={showEditSupplier} onOpenChange={setShowEditSupplier}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Supplier</DialogTitle>
            <DialogDescription>Update supplier details</DialogDescription>
          </DialogHeader>
          {selectedSupplier && (
            <div className="space-y-4">
              <div>
                <Label>Name</Label>
                <Input
                  value={selectedSupplier.name}
                  onChange={(e) => setSelectedSupplier({ ...selectedSupplier, name: e.target.value })}
                />
              </div>
              <div>
                <Label>Email</Label>
                <Input value={selectedSupplier.email} disabled className="bg-gray-100" />
              </div>
              <div>
                <Label>Company Name</Label>
                <Input
                  value={selectedSupplier.company_name || ''}
                  onChange={(e) => setSelectedSupplier({ ...selectedSupplier, company_name: e.target.value })}
                />
              </div>
              <div className="flex items-center gap-3">
                <Switch
                  id="supplier-active"
                  checked={selectedSupplier.is_active !== false}
                  onCheckedChange={(checked) => setSelectedSupplier({ ...selectedSupplier, is_active: checked })}
                />
                <Label htmlFor="supplier-active">Active Account</Label>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditSupplier(false)}>Cancel</Button>
            <Button onClick={handleUpdateSupplier} className="bg-yellow-600 hover:bg-yellow-700">Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminDashboard;
