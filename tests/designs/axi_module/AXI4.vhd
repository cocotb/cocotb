-- Copyright 2019 by Ben Coughlan <ben@liquidinstruments.com>
--
-- Licensed under Revised BSD License
-- All rights reserved. See LICENSE.

library IEEE;
use IEEE.Std_Logic_1164.all;
use IEEE.Numeric_Std.all;

-- Just a simple shim entity for cocotb to run tests against itself.

entity AXI4_Shim is
	port (
		Clk : in std_logic;
		Reset : in std_logic;

		-- Write Bus
		SAXI_awid : in std_logic_vector(5 downto 0);
		SAXI_awaddr : in std_logic_vector(31 downto 0);
		SAXI_awlen : in std_logic_vector(7 downto 0);
		SAXI_awsize : in std_logic_vector(2 downto 0);
		SAXI_awburst : in std_logic_vector(1 downto 0);
		SAXI_awlock : in std_logic_vector(1 downto 0);
		SAXI_awcache : in std_logic_vector(3 downto 0);
		SAXI_awprot : in std_logic_vector(2 downto 0);
		SAXI_awqos : in std_logic_vector(3 downto 0);
		SAXI_awvalid : in std_logic;
		SAXI_awready : out std_logic;

		SAXI_wid : in std_logic_vector(5 downto 0);
		SAXI_wdata : in std_logic_vector(63 downto 0);
		SAXI_wstrb : in std_logic_vector(7 downto 0);
		SAXI_wlast : in std_logic;
		SAXI_wvalid : in std_logic;
		SAXI_wready : out std_logic;

		SAXI_bid : out std_logic_vector(5 downto 0);
		SAXI_bresp : out std_logic_vector(1 downto 0);
		SAXI_bvalid : out std_logic;
		SAXI_bready : in std_logic;

		SAXI_arid : in std_logic_vector(5 downto 0);
		SAXI_araddr : in std_logic_vector(31 downto 0);
		SAXI_arlen : in std_logic_vector(3 downto 0);
		SAXI_arsize : in std_logic_vector(2 downto 0);
		SAXI_arburst : in std_logic_vector(1 downto 0);
		SAXI_arlock : in std_logic_vector(1 downto 0);
		SAXI_arcache : in std_logic_vector(3 downto 0);
		SAXI_arprot : in std_logic_vector(2 downto 0);
		SAXI_arqos : in std_logic_vector(3 downto 0);
		SAXI_arvalid : in std_logic;
		SAXI_arready : out std_logic;

		SAXI_rid : out std_logic_vector(5 downto 0);
		SAXI_rdata : out std_logic_vector(63 downto 0);
		SAXI_rresp : out std_logic_vector(1 downto 0);
		SAXI_rlast : out std_logic;
		SAXI_rvalid : out std_logic;
		SAXI_rready : in std_logic;

		-- Write Address Channel
		MAXI_awid : out std_logic_vector(5 downto 0);
		MAXI_awaddr : out std_logic_vector(31 downto 0);
		MAXI_awlen : out std_logic_vector(7 downto 0);
		MAXI_awsize : out std_logic_vector(2 downto 0);
		MAXI_awburst : out std_logic_vector(1 downto 0);
		MAXI_awlock : out std_logic_vector(1 downto 0);
		MAXI_awcache : out std_logic_vector(3 downto 0);
		MAXI_awprot : out std_logic_vector(2 downto 0);
		MAXI_awqos : out std_logic_vector(3 downto 0);
		MAXI_awvalid : out std_logic;
		MAXI_awready : in std_logic;

		--Write Data Channel
		MAXI_wid : out std_logic_vector(5 downto 0);
		MAXI_wdata : out std_logic_vector(63 downto 0);
		MAXI_wstrb : out std_logic_vector(7 downto 0);
		MAXI_wlast : out std_logic;
		MAXI_wvalid : out std_logic;
		MAXI_wready : in std_logic;

		--Write Response Channel
		MAXI_bid : in std_logic_vector(5 downto 0);
		MAXI_bresp : in std_logic_vector(1 downto 0);
		MAXI_bvalid : in std_logic;
		MAXI_bready : out std_logic;

		--Read Address Channel
		MAXI_arid : out std_logic_vector(5 downto 0);
		MAXI_araddr : out std_logic_vector(31 downto 0);
		MAXI_arlen : out std_logic_vector(3 downto 0);
		MAXI_arsize : out std_logic_vector(2 downto 0);
		MAXI_arburst : out std_logic_vector(1 downto 0);
		MAXI_arlock : out std_logic_vector(1 downto 0);
		MAXI_arcache : out std_logic_vector(3 downto 0);
		MAXI_arprot : out std_logic_vector(2 downto 0);
		MAXI_arqos : out std_logic_vector(3 downto 0);
		MAXI_arvalid : out std_logic;
		MAXI_arready : in std_logic;

		--Read Response Channel
		MAXI_rid : in std_logic_vector(5 downto 0);
		MAXI_rdata : in std_logic_vector(63 downto 0);
		MAXI_rresp : in std_logic_vector(1 downto 0);
		MAXI_rlast : in std_logic;
		MAXI_rvalid : in std_logic;
		MAXI_rready : out std_logic
	);
end entity;

architecture Behavioural of AXI4_Shim is
begin
	MAXI_arid <= SAXI_arid;
	MAXI_araddr <= SAXI_araddr;
	MAXI_arlen <= SAXI_arlen;
	MAXI_arsize <= SAXI_arsize;
	MAXI_arburst <= SAXI_arburst;
	MAXI_arvalid <= SAXI_arvalid;
	SAXI_arready <= MAXI_arready;
	MAXI_arlock <= SAXI_arlock;
	MAXI_arcache <= SAXI_arcache;
	MAXI_arprot <= SAXI_arprot;
	MAXI_arqos <= SAXI_arqos;

	SAXI_rid <= MAXI_rid;
	SAXI_rdata <= MAXI_rdata;
	SAXI_rresp <= MAXI_rresp;
	SAXI_rlast <= MAXI_rlast;
	SAXI_rvalid <= MAXI_rvalid;
	MAXI_rready <= SAXI_rready;

	MAXI_awid <= SAXI_awid;
	MAXI_awaddr <= SAXI_awaddr;
	MAXI_awlen <= SAXI_awlen;
	MAXI_awsize <= SAXI_awsize;
	MAXI_awburst <= SAXI_awburst;
	MAXI_awlock <= SAXI_awlock;
	MAXI_awcache <= SAXI_awcache;
	MAXI_awprot <= SAXI_awprot;
	MAXI_awqos <= SAXI_awqos;
	MAXI_awvalid <= SAXI_awvalid;
	SAXI_awready <= MAXI_awready;

	MAXI_wid <= SAXI_wid;
	MAXI_wdata <= SAXI_wdata;
	MAXI_wstrb <= SAXI_wstrb;
	MAXI_wlast <= SAXI_wlast;
	MAXI_wvalid <= SAXI_wvalid;
	SAXI_wready <= MAXI_wready;

	SAXI_bid <= MAXI_bid;
	SAXI_bresp <= MAXI_bresp;
	SAXI_bvalid <= MAXI_bvalid;
	MAXI_bready <= SAXI_bready;
end architecture;
