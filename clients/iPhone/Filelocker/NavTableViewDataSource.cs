using System;
using System.Collections.Generic;
using MonoTouch.UIKit;
using MonoTouch.Foundation;

namespace Filelocker
{
	//========================================================================

	//
	// The data source for our Navigation TableView
	//
	
	public class NavTableViewDataSource : UITableViewDataSource
	{
		/// <summary>
		/// The collection of Navigation Items that we bind to our Navigation Table
		/// </summary>
	
		public List<NavItem> NavItems
		{
			get { return this._navItems; }
			set { this._navItems = value; }
		}
	
		protected List<NavItem> _navItems;

		/// <summary>
		/// Constructor
		/// </summary>
	
		public NavTableViewDataSource (List<NavItem> navItems)
		{
			this._navItems = navItems;
		}
	
		/// <summary>
		/// Called by the TableView to determine how man cells to create for that particular section.
		/// </summary>
	
		public override int RowsInSection (UITableView tableView, int section)
		{
			return this._navItems.Count;
		}
		
		/// <summary>
		/// Called by the TableView to actually build each cell. 
		/// </summary>
	
		public override UITableViewCell GetCell (UITableView tableView, NSIndexPath indexPath)
		{
			//---- declare vars
	
			string cellIdentifier = "SimpleCellTemplate";
	
			//---- try to grab a cell object from the internal queue
	
			var cell = tableView.DequeueReusableCell (cellIdentifier);
	
			//---- if there wasn't any available, just create a new one
	
			if (cell == null)
			{
				cell = new UITableViewCell (UITableViewCellStyle.Default, cellIdentifier);
			}
	
			//---- set the cell properties
	
			cell.TextLabel.Text = this._navItems[indexPath.Row].Name;
			cell.Accessory = UITableViewCellAccessory.DisclosureIndicator;
			
			//---- return the cell
			return cell;
		}
	
	}
	
	//====================================================================
}