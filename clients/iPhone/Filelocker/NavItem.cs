using System;
using MonoTouch.UIKit;
namespace Filelocker
{
	public class NavItem
	{
		#region -= declarations =-
		
		/// <summary>
		///  The name of the nav item, shows up as the label
		/// </summary>
		
		public string Name
		{
			get { return this._name;}
			set { this._name = value;}
		}
		
		protected string _name;
		
		/// <summary>
		/// The UIViewController that the nav item opens. Use this property if you wanted to
		/// early instantiate the controller when the nav table is built out,
		/// otherwise just set the Type property and it will lazy-instantiate when the
		/// nav item is clicked on
		/// </summary>
		
		public UIViewController Controller
		{
			get { return this._controller; }
			set { this._controller = value; }
		}
		protected UIViewController _controller;
		
		/// <summary>
		/// The type of the UIViewController. Set this to the type and leave the Controller
		/// property empty to lazy-instantiate the ViewController when the nav item is 
		/// clicked
		/// </summary>
		
		public Type ControllerType
		{
			get { return this._controllerType;}
			set { this._controllerType = value;}
		}
		protected Type _controllerType;
		
		
		/// <summary>
		/// a list of the constructor args (if neccesary) for the controller. use this in
		/// conjunction with ControllerType if lazy-creating controllers.
		/// </summary>

		public object[] ControllerConstructorArgs
		{
			get { return this._controllerConstructorArgs; }
			set	
			{
				this._controllerConstructorArgs = value;
				this._controllerConstructorTypes = new Type[this._controllerConstructorArgs.Length];

				for (int i = 0; i < this._controllerConstructorArgs.Length; i++)
				{
					this._controllerConstructorTypes[i] = this._controllerConstructorArgs[i].GetType();
				}
         	}
		}

		protected object[] _controllerConstructorArgs = new object[] {};



        /// <summary>
        /// The types of constructor args.
        /// </summary>
        public Type[] ControllerConstructorTypes
        {
        	get { return this._controllerConstructorTypes; }
        }

        protected Type[] _controllerConstructorTypes = Type.EmptyTypes;
     	#endregion


         //========================================================================



         //========================================================================

         #region -= constructors =-



         public NavItem ()

         {

         }



		public NavItem (string name) : this()
		{
			this._name = name;
		}

		public NavItem (string name, UIViewController controller) : this(name)
		{
			this._controller = controller;
		}

     	public NavItem (string name, Type controllerType) : this(name)
        {
			this._controllerType = controllerType;
		}

		public NavItem (string name, Type controllerType, object[] controllerConstructorArgs) : this(name, controllerType)
		{
			this.ControllerConstructorArgs = controllerConstructorArgs;
		}

		#endregion
	}
}