"use client";

import { useState } from "react";
import {
  useConnections,
  useCreateConnection,
  useDeleteConnection,
  useSyncConnection,
} from "@/hooks/api/useConnections";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Loader2, Wifi, WifiOff, RefreshCw, Trash2, Plus } from "lucide-react";

export default function ConnectionsPage() {
  const [showAddModal, setShowAddModal] = useState(false);
  const [newConnection, setNewConnection] = useState({
    broker_name: "MetaTrader 5",
    account_number: "",
    server: "",
  });

  const { data: connections = [], isLoading } = useConnections();
  const createConnection = useCreateConnection();
  const deleteConnection = useDeleteConnection();
  const syncConnection = useSyncConnection();

  const handleCreateConnection = async () => {
    await createConnection.mutateAsync(newConnection);
    setShowAddModal(false);
    setNewConnection({ broker_name: "MetaTrader 5", account_number: "", server: "" });
  };

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this connection?")) {
      await deleteConnection.mutateAsync(id);
    }
  };

  const handleSync = async (id: string) => {
    await syncConnection.mutateAsync(id);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Broker Connections</h1>
          <p className="text-muted-foreground mt-1">
            Connect your MT5 broker accounts using the Windows connector app
          </p>
        </div>
        <Button onClick={() => setShowAddModal(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Add Connection
        </Button>
      </div>

      {/* Instructions */}
      <Card className="border-blue-500/30 bg-blue-500/5">
        <CardContent className="pt-6">
          <div className="flex gap-3">
            <div className="text-blue-500">ℹ️</div>
            <div className="text-sm">
              <p className="font-medium text-blue-400">How to connect:</p>
              <ol className="list-decimal list-inside mt-2 text-muted-foreground space-y-1">
                <li>Download and install the MT5 Connector app (Windows)</li>
                <li>Add a connection here with your broker details</li>
                <li>Open the connector app and login to your MT5 account</li>
                <li>The connector will automatically sync your trades</li>
              </ol>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Connections List */}
      <div className="grid gap-4">
        {isLoading ? (
          <Card>
            <CardContent className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </CardContent>
          </Card>
        ) : connections.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <WifiOff className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No broker connections yet</p>
              <p className="text-sm text-muted-foreground mt-1">
                Add a connection to start syncing your trades
              </p>
            </CardContent>
          </Card>
        ) : (
          connections.map((conn) => (
            <Card key={conn.id}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-3 h-3 rounded-full ${
                        conn.is_active ? "bg-green-500" : "bg-gray-500"
                      }`}
                    />
                    <div>
                      <CardTitle className="text-lg">{conn.broker_name}</CardTitle>
                      <CardDescription>
                        {conn.account_number
                          ? `Account: ${conn.account_number}`
                          : "No account linked"}
                        {conn.server && ` • ${conn.server}`}
                      </CardDescription>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {conn.is_active ? (
                      <span className="flex items-center gap-1 text-sm text-green-500">
                        <Wifi className="w-4 h-4" />
                        Connected
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-sm text-muted-foreground">
                        <WifiOff className="w-4 h-4" />
                        Offline
                      </span>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    {conn.last_connected_at
                      ? `Last connected: ${new Date(conn.last_connected_at).toLocaleString()}`
                      : "Never connected"}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleSync(conn.id)}
                      disabled={syncConnection.isPending}
                    >
                      <RefreshCw className="w-4 h-4 mr-1" />
                      Sync
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => handleDelete(conn.id)}
                      disabled={deleteConnection.isPending}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Add Connection Modal */}
      <Dialog open={showAddModal} onOpenChange={setShowAddModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Broker Connection</DialogTitle>
            <DialogDescription>
              Enter your broker account details to set up the connection
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="broker">Broker Platform</Label>
              <Input
                id="broker"
                value={newConnection.broker_name}
                onChange={(e) =>
                  setNewConnection({ ...newConnection, broker_name: e.target.value })
                }
                placeholder="MetaTrader 5"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="account">Account Number (optional)</Label>
              <Input
                id="account"
                value={newConnection.account_number}
                onChange={(e) =>
                  setNewConnection({ ...newConnection, account_number: e.target.value })
                }
                placeholder="12345678"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="server">Server (optional)</Label>
              <Input
                id="server"
                value={newConnection.server}
                onChange={(e) =>
                  setNewConnection({ ...newConnection, server: e.target.value })
                }
                placeholder="Exness-MT5Real"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateConnection}
              disabled={createConnection.isPending}
            >
              {createConnection.isPending ? "Creating..." : "Add Connection"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
