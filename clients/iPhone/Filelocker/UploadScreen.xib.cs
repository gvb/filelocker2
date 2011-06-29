
using System;
using System.Collections.Generic;
using MonoTouch.Foundation;
using MonoTouch.UIKit;
using MonoTouch.AssetsLibrary;

namespace Filelocker
{
	public partial class UploadScreen : UIViewController
	{
		#region Constructors

		// The IntPtr and initWithCoder constructors are required for items that need 
		// to be able to be created from a xib rather than from managed code

		public UploadScreen (IntPtr handle) : base(handle)
		{
			Initialize ();
		}

		[Export("initWithCoder:")]
		public UploadScreen (NSCoder coder) : base(coder)
		{
			Initialize ();
		}

		public UploadScreen () : base("UploadScreen", null)
		{
			Initialize ();
		}

		void Initialize ()
		{
		}
		ALAssetsLibrary assetsLibrary;
		public override void ViewDidLoad() 
		{
			base.ViewDidLoad();
			assetsLibrary = new ALAssetsLibrary();
			StartEnumeration();
			Console.WriteLine("Assets have been loaded");
		}
		private void StartEnumeration()
		{
			this.assetsLibrary = new ALAssetsLibrary();
			this.assetsLibrary.Enumerate(ALAssetsGroupType.All, this.GroupsEnumeration, this.GroupsEnumerationFailure);
		}
		private void GroupsEnumeration(ALAssetsGroup group, ref bool stop)
		{
			if (group != null)
			{
				stop = false;
				group.SetAssetsFilter(ALAssetsFilter.AllAssets);
				group.Enumerate(this.AssetsEnumeration);
			}
		}
		private void GroupsEnumerationFailure(NSError error)
		{
			if (error != null)
			{
				Console.WriteLine("Group enumeration failed! {0}", error.LocalizedDescription);
			}
		}
		private void AssetsEnumeration(ALAsset asset, int index, ref bool stop)
		{
			if (asset != null)
			{
				stop = false;
			}
		}
		#endregion
	}
}

