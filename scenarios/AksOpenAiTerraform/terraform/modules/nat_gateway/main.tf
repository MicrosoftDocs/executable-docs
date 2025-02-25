resource "azurerm_nat_gateway" "this" {
  name                    = var.name
  location                = var.location
  resource_group_name     = var.resource_group_name
}

resource "azurerm_public_ip" "nat_gateway" {
  name                = "${var.name}PublicIp"
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
}

resource "azurerm_nat_gateway_public_ip_association" "nat_gategay_public_ip_association" {
  nat_gateway_id       = azurerm_nat_gateway.this.id
  public_ip_address_id = azurerm_public_ip.nat_gateway.id
}

resource "azurerm_subnet_nat_gateway_association" "gateway_association" {
  for_each       = var.subnet_ids
  subnet_id      = each.value
  nat_gateway_id = azurerm_nat_gateway.this.id
}