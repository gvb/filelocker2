using System;
using MonoTouch.Foundation;
using MonoTouch.UIKit;
using System.Collections.Generic;
using System.Reflection;

namespace Filelocker
{
	public class NavTableDelegate : UITableViewDelegate
	{
		UINavigationController _navigationController;
		List<NavItem> _navItems;
		public NavTableDelegate (UINavigationController navigationController, List<NavItem> navItems)
		{
			this._navigationController = navigationController;
			this._navItems = navItems;
		}


		//========================================================================
		/// <summary>
		/// Is called when a row is selected
		/// </summary>

		public override void RowSelected (UITableView tableView, NSIndexPath indexPath)
		{
			//---- get a reference to the nav item
			NavItem navItem = this._navItems[indexPath.Row];
	
			//---- if the nav item has a proper controller, push it on to the NavigationController
			// NOTE: we could also raise an event here, to loosely couple this, but isn't neccessary,
			// because we'll only ever use this this way
	
			if (navItem.Controller != null)
			{
				this._navigationController.PushViewController (navItem.Controller, true);
				//---- show the nav bar (we don't show it on the home page)
				this._navigationController.NavigationBarHidden = false;
	
			} 
			else
			{
				if (navItem.ControllerType != null)
				{
					//----
					ConstructorInfo ctor = null;
	
					//---- if the nav item has constructor aguments
					if (navItem.ControllerConstructorArgs.Length > 0)
					{
						//---- look for the constructor
						ctor = navItem.ControllerType.GetConstructor (navItem.ControllerConstructorTypes);
					} 
					else
					{
						//---- search for the default constructor
						ctor = navItem.ControllerType.GetConstructor (System.Type.EmptyTypes);
					}
	
					//---- if we found the constructor
					if (ctor != null)
					{
						//----
						UIViewController instance = null;
	
						if (navItem.ControllerConstructorArgs.Length > 0)
						{
							//---- instance the view controller
							instance = ctor.Invoke (navItem.ControllerConstructorArgs) as UIViewController;
	
						} 
						else
						{
							//---- instance the view controller
							instance = ctor.Invoke (null) as UIViewController;
						}
	
						if (instance != null)
						{
							//---- save the object
							navItem.Controller = instance;
	
							//---- push the view controller onto the stack
							this._navigationController.PushViewController (navItem.Controller, true);
	
						} 
						else
						{
							Console.WriteLine ("instance of view controller not created");
						}
	
					} 
					else
					{
						Console.WriteLine ("constructor not found");
					}
				}
			}
		}
	}
}